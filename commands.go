package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/mrcsin/coub-dl/internal/coub"
)

func cmdDownload(ctx context.Context, args []string) int {
	fs := flag.NewFlagSet("download", flag.ContinueOnError)
	destDir := fs.String("out", ".", "output directory")
	name := fs.String("name", "", "output file name (without extension; defaults to the coub id)")
	if err := fs.Parse(args); err != nil {
		return 64
	}

	rest := fs.Args()
	if len(rest) != 1 {
		fmt.Fprintln(os.Stderr, "expected exactly one link or permalink, e.g. https://coub.com/view/2uywin")
		return 64
	}

	permalink := extractPermalink(rest[0])
	if permalink == "" {
		fmt.Fprintln(os.Stderr, "could not extract a permalink from the link")
		return 64
	}

	if err := checkFFmpeg(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}

	hc := &http.Client{Timeout: 60 * time.Second}
	client := coub.NewClient(hc, "")

	cb, err := client.Get(ctx, permalink)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetching coub: %v\n", err)
		return 1
	}

	path, _, err := client.Download(ctx, cb, *destDir, *name)
	if err != nil {
		fmt.Fprintf(os.Stderr, "downloading coub: %v\n", err)
		return 1
	}

	fmt.Println(path)
	return 0
}

func cmdSync(ctx context.Context, args []string) int {
	token := os.Getenv("API_TOKEN")
	if token == "" {
		fmt.Fprintln(os.Stderr, "API_TOKEN is not set")
		return 64
	}

	fs := flag.NewFlagSet("sync", flag.ContinueOnError)
	outDir := fs.String("out", "videos", "output directory")
	workers := fs.Int("workers", 5, "concurrent downloads")
	if err := fs.Parse(args); err != nil {
		return 64
	}
	if *workers < 1 {
		*workers = 1
	}

	if err := checkFFmpeg(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 1
	}

	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.MaxIdleConns = 100
	transport.MaxIdleConnsPerHost = max(*workers*2, 10)
	hc := &http.Client{Transport: transport, Timeout: 60 * time.Second}

	client := coub.NewClient(hc, token)

	total, err := client.LikesCount(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetching likes: %v\n", err)
		return 1
	}
	fmt.Fprintf(os.Stderr, "syncing ~%d liked coubs\n", total)

	coubs, errCh := client.FetchLikes(ctx)

	s := &syncer{client: client, outDir: *outDir, workers: *workers, total: total}
	res := s.run(ctx, coubs)

	err = <-errCh
	if err != nil && !errors.Is(err, context.Canceled) {
		fmt.Fprintln(os.Stderr, "error:", err)
		return 1
	}

	if ctx.Err() != nil {
		reportResult(res, true)
		return 130
	}

	reportResult(res, false)
	return 0
}

func checkFFmpeg() error {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		return fmt.Errorf("ffmpeg not found in PATH (required to combine video and audio)")
	}
	return nil
}

type syncResult struct {
	ok      int
	skipped int
	failed  int
}

type outcome int

const (
	outcomeOK outcome = iota
	outcomeSkipped
	outcomeFailed
)

type result struct {
	permalink string
	outcome   outcome
	err       error
}

type syncer struct {
	client  *coub.Client
	outDir  string
	workers int
	total   int
}

func (s *syncer) run(ctx context.Context, coubs <-chan coub.Coub) syncResult {
	var wg sync.WaitGroup
	sem := make(chan struct{}, s.workers)
	results := make(chan result, s.workers)

	tally := make(chan syncResult, 1)
	go func() { tally <- report(results, s.total) }()

	seen := make(map[string]bool)
dispatch:
	for cb := range coubs {
		if seen[cb.Permalink] {
			continue
		}
		seen[cb.Permalink] = true

		select {
		case <-ctx.Done():
			break dispatch
		case sem <- struct{}{}:
		}

		wg.Add(1)
		go func(cb coub.Coub) {
			defer wg.Done()
			defer func() { <-sem }()

			r := s.download(ctx, cb)
			if ctx.Err() != nil {
				return
			}
			results <- r
		}(cb)
	}

	wg.Wait()
	close(results)
	return <-tally
}

func (s *syncer) download(ctx context.Context, cb coub.Coub) result {
	_, skipped, err := s.client.Download(ctx, cb, s.dest(cb), "")
	switch {
	case err != nil:
		return result{cb.Permalink, outcomeFailed, err}
	case skipped:
		return result{cb.Permalink, outcomeSkipped, nil}
	default:
		return result{cb.Permalink, outcomeOK, nil}
	}
}

func (s *syncer) dest(cb coub.Coub) string {
	return dateDir(s.outDir, cb.UpdatedAt)
}

func report(results <-chan result, total int) syncResult {
	var res syncResult
	done := 0
	for r := range results {
		done++
		switch r.outcome {
		case outcomeFailed:
			res.failed++
			fmt.Fprintf(os.Stderr, "[%d/%d] FAIL %s: %v\n", done, total, r.permalink, r.err)
		case outcomeSkipped:
			res.skipped++
			fmt.Fprintf(os.Stderr, "[%d/%d] skip %s\n", done, total, r.permalink)
		default:
			res.ok++
			fmt.Fprintf(os.Stderr, "[%d/%d] ok   %s\n", done, total, r.permalink)
		}
	}
	return res
}

func reportResult(res syncResult, cancelled bool) {
	prefix := "done:"
	if cancelled {
		prefix = "cancelled."
	}
	fmt.Fprintf(os.Stderr, "%s %d downloaded, %d skipped, %d failed\n",
		prefix, res.ok, res.skipped, res.failed)
}

func extractPermalink(arg string) string {
	if i := strings.LastIndex(arg, "view/"); i != -1 {
		arg = arg[i+len("view/"):]
	}
	arg = strings.SplitN(arg, "/", 2)[0]
	arg = strings.SplitN(arg, "?", 2)[0]
	return arg
}

func dateDir(baseDir, updatedAt string) string {
	if len(updatedAt) < 7 {
		return baseDir
	}
	ym := updatedAt[:7]
	return filepath.Join(baseDir, ym[:4], ym[5:7])
}

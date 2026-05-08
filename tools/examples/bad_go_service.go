package main

import (
	"bytes"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime"
	"runtime/pprof"
	"strconv"
	"sync"
	"time"
)

var (
	leakedMemory [][]byte
	leakMu       sync.Mutex
)

func main() {
	selfTest := flag.Bool("self-test", false, "start built-in bad workloads without opening an HTTP port")
	dumpPath := flag.String("dump", "/tmp/bad_go_goroutine.log", "goroutine dump path for --self-test")
	hold := flag.Duration("hold", 2*time.Minute, "how long --self-test keeps the process alive")
	flag.Parse()

	if *selfTest {
		runSelfTest(*dumpPath, *hold)
		return
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/", indexHandler)
	mux.HandleFunc("/cpu", cpuHandler)
	mux.HandleFunc("/leak", leakHandler)
	mux.HandleFunc("/mem", memoryHandler)
	mux.HandleFunc("/block", blockHandler)
	mux.HandleFunc("/debug/goroutines", goroutineDumpHandler)

	server := &http.Server{
		Addr:    "127.0.0.1:18080",
		Handler: mux,
	}

	log.Println("bad go service listening on http://127.0.0.1:18080")
	log.Println("endpoints: /cpu?n=4 /leak?n=2000 /mem?mb=256 /block?n=200 /debug/goroutines")
	if err := server.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func runSelfTest(dumpPath string, hold time.Duration) {
	log.Println("self-test mode: starting intentionally bad workloads")
	startCPUBurners(1)
	startBlockedReceivers(800)
	startSleepingGoroutines(100)
	retainMemory(32)

	file, err := os.Create(dumpPath)
	if err != nil {
		log.Fatalf("create dump file: %v", err)
	}
	if err := pprof.Lookup("goroutine").WriteTo(file, 2); err != nil {
		_ = file.Close()
		log.Fatalf("write goroutine dump: %v", err)
	}
	_ = file.Close()

	log.Printf("goroutine dump written to %s", dumpPath)
	log.Printf("holding process for %s, pid=%d", hold, os.Getpid())
	time.Sleep(hold)
}

func indexHandler(w http.ResponseWriter, _ *http.Request) {
	fmt.Fprintln(w, "bad go service is running")
	fmt.Fprintln(w, "try: /cpu?n=4 /leak?n=2000 /mem?mb=256 /block?n=200 /debug/goroutines")
}

func cpuHandler(w http.ResponseWriter, r *http.Request) {
	n := queryInt(r, "n", runtime.NumCPU())
	startCPUBurners(n)
	fmt.Fprintf(w, "started %d CPU burning goroutines\n", n)
}

func leakHandler(w http.ResponseWriter, r *http.Request) {
	n := queryInt(r, "n", 1000)
	startBlockedReceivers(n)
	fmt.Fprintf(w, "started %d blocked goroutines on chan receive\n", n)
}

func memoryHandler(w http.ResponseWriter, r *http.Request) {
	mb := queryInt(r, "mb", 128)
	retainMemory(mb)
	leakMu.Lock()
	total := len(leakedMemory)
	leakMu.Unlock()
	fmt.Fprintf(w, "allocated and retained %d MB, retained chunks=%d\n", mb, total)
}

func blockHandler(w http.ResponseWriter, r *http.Request) {
	n := queryInt(r, "n", 100)
	startSleepingGoroutines(n)
	fmt.Fprintf(w, "started %d sleeping goroutines\n", n)
}

func startCPUBurners(n int) {
	for i := 0; i < n; i++ {
		go func(worker int) {
			log.Printf("start cpu burner worker=%d", worker)
			for {
			}
		}(i)
	}
}

func startBlockedReceivers(n int) {
	ch := make(chan struct{})
	for i := 0; i < n; i++ {
		go func() {
			<-ch
		}()
	}
}

func retainMemory(mb int) {
	if mb < 1 {
		mb = 1
	}
	chunk := bytes.Repeat([]byte("x"), mb*1024*1024)
	leakMu.Lock()
	leakedMemory = append(leakedMemory, chunk)
	leakMu.Unlock()
}

func startSleepingGoroutines(n int) {
	for i := 0; i < n; i++ {
		go func() {
			time.Sleep(30 * time.Minute)
		}()
	}
}

func goroutineDumpHandler(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	_ = pprof.Lookup("goroutine").WriteTo(w, 2)
}

func queryInt(r *http.Request, key string, fallback int) int {
	raw := r.URL.Query().Get(key)
	if raw == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return value
}

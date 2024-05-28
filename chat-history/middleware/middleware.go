package middleware

import (
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"time"

	"github.com/go-chi/httplog/v2"
)

type Middleware func(http.Handler) http.Handler

func ChainMiddleware(handler http.Handler, middle ...Middleware) http.Handler {
	for _, m := range middle {
		handler = m(handler)
	}

	return handler
}

// logger
type logger struct {
	f *os.File
}

// logger init
func initLogger(fname string) logger {
	f, err := os.OpenFile(fname, os.O_RDWR|os.O_CREATE, 0644)
	if err != nil {
		panic(err)
	}
	return logger{f}
}

// impl io.Writer interface
func (l logger) Write(b []byte) (int, error) {
	n, err := l.f.Write(b)
	fmt.Println(string(b))
	return n, err
}

// init logger middleware
func Logger() func(http.Handler) http.Handler {
	fname := "logs.jsonl"
	// TODO: don't use after dev
	if _, e := os.Stat(fname); e == nil {
		err := os.Remove(fname)
		if err != nil {
			panic(err)
		}
	}

	l := initLogger(fname)

	logger := httplog.NewLogger("httplog", httplog.Options{
		JSON:             true,
		LogLevel:         slog.LevelDebug,
		Concise:          true,
		RequestHeaders:   false,
		MessageFieldName: "message",
		// TimeFieldFormat: time.RFC850,
		// Tags: map[string]string{
		// 	// "version": "v1.0-81aa4244d9fc8076a",
		// 	// "env": "dev",
		// },
		QuietDownRoutes: []string{
			"/",
		},
		QuietDownPeriod: 10 * time.Second,
		// SourceFieldName: "source",
		Writer: l,
	})

	return httplog.RequestLogger(logger)
}

func Auth(next http.Handler) http.Handler {
	fn := func(w http.ResponseWriter, r *http.Request) {
		// fmt.Println(r.Header["Authorization"])
		// fmt.Println("hellllllo")
		next.ServeHTTP(w, r)
	}
	return http.HandlerFunc(fn)
}

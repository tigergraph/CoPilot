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

// TODO:
func Logger() func(http.Handler) http.Handler {
	fmt.Println("hello from logger")

	// create a io.writer for the logger to use so that
	// the logger can write to a file
	// make custom writer to log to file based on log level?
	f, err := os.Open("")
	if err != nil {
		panic(err)
	}

	logger := httplog.NewLogger("httplog-example", httplog.Options{
		// JSON:             true,
		LogLevel:         slog.LevelDebug,
		Concise:          true,
		RequestHeaders:   true,
		MessageFieldName: "message",
		// TimeFieldFormat: time.RFC850,
		Tags: map[string]string{
			// "version": "v1.0-81aa4244d9fc8076a",
			"env": "dev",
		},
		QuietDownRoutes: []string{
			"/",
		},
		QuietDownPeriod: 10 * time.Second,
		// SourceFieldName: "source",
		Writer: f,
	})

	return httplog.RequestLogger(logger)
}

// TODO:
func Auth(next http.Handler) http.Handler {
	fn := func(w http.ResponseWriter, r *http.Request) {
		fmt.Println("hellllllo")
		next.ServeHTTP(w, r)
	}
	return http.HandlerFunc(fn)
}

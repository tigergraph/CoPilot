if [[ ! -f k6 ]]; then
	echo "downloading k6-dashboard"
	curl -L https://github.com/grafana/xk6-dashboard/releases/download/v0.7.2/xk6-dashboard_v0.7.2_darwin_amd64.tar.gz | tar xz
	rm LICENSE README.md
fi

if [[ $# -lt 1 ]]; then
	./k6 run --out web-dashboard=export=test-report.html script.js
else
	echo "Saving to $1.html"
	./k6 run --out web-dashboard=export=$1.html script.js
fi

# rm k6

.PHONY: help install scaffold ingest test serve clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python package and dependencies
	pip3 install -e ".[dev]"
	@echo ""
	@echo "✓ Artifactor installed successfully"
	@echo "  Run 'make scaffold' to generate a sample post"

scaffold: ## Generate sample post from fixture
	python3 -m artifactor scaffold --out site/ --fixture fixtures/sample_article.json
	@echo ""
	@echo "✓ Post generated successfully"
	@echo "  Check site/_posts/ for the generated file"

ingest: ## Ingest URLs (offline demo, dry-run)
	@echo "Running offline ingestion demo (no network, dry-run)..."
	@echo "Using fixture HTML from fixtures/socket_article_sample.html"
	@echo ""
	python3 -m artifactor ingest --urls fixtures/urls_sample.txt --out site/ --limit 1 --dry-run --html-fixture fixtures/socket_article_sample.html
	@echo ""
	@echo "To ingest from real URLs, run:"
	@echo "  python3 -m artifactor ingest --urls your_urls.txt --out site/"

test: ## Run test suite
	python3 -m pytest -v
	@echo ""
	@echo "✓ All tests passed"

serve: ## Start Jekyll development server
	@echo "Starting Jekyll server..."
	@echo "Prerequisites: Ruby + Bundler installed"
	@echo "  First time: cd site && bundle install"
	@echo ""
	cd site && bundle exec jekyll serve
	@echo ""
	@echo "Server stopped"

clean: ## Remove generated site files and caches
	@echo "Cleaning build artifacts..."
	rm -rf site/_site/
	rm -rf site/.jekyll-cache/
	rm -rf site/.jekyll-metadata
	@echo "✓ Cleaned successfully"

FROM docker:cli AS dk
FROM python:3.12-slim
COPY --from=dk /usr/local/bin/docker /usr/local/bin/docker
RUN pip install --no-cache-dir pyyaml numpy
WORKDIR /ai-server/bench_results
CMD ["sh", "/ai-server/benchmarks/run_container.sh"]

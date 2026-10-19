docker compose up -d
docker compose run --build --rm competitors
docker compose --profile collection run --rm --build competitors --execute --limit-runs 1
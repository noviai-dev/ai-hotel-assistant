docker compose up -d

docker compose run --build --rm competitors
### 采集一次
docker compose --profile collection run --rm --build competitors --execute --limit-runs 1



docker-compose.exe up -d
docker-compose.exe down


### 查询总记录条数
docker exec -it ai-hotel-assistant-postgres-1 psql -U postgres -d postgres -c "SELECT COUNT(*) FROM hotel_quotes;"
### 查询最近采集时间
docker exec -it ai-hotel-assistant-postgres-1 psql -U postgres -d postgres -c "SELECT collected_at FROM hotel_quotes ORDER BY collected_at desc limit 1;"


wsl: 
ssh -i ~/.ssh/AssistantConsole.pem ubuntu@ec2-57-181-40-228.ap-northeast-1.compute.amazonaws.com
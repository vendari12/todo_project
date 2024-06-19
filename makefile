run:
# Starts all the development containers
	docker compose up postgres -d
	sleep 2
	docker compose up todo -d
	sleep 2
	docker exec -i todo python manage.py create-tables
	sleep 2
	docker exec -i todo python manage.py setup-dev
	sleep 2
	docker compose --profile dev up 
	
build:
# Rebuilds the container images
	docker compose --profile dev up	--build

test:
# Runs the test suites
	docker compose --profile test up -d
	sleep 1
	docker exec todo pytest tests
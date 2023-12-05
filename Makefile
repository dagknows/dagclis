
down:
	sudo docker-compose down

build: down
	sudo docker-compose up --build -d

up: down
	sudo docker-compose up -d

logs:
	sudo docker-compose logs -f

update: pull down build up logs

pull:
	sudo docker pull gcr.io/dagknows-proxy-images/cmd_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/script_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/agent_frontend:latest

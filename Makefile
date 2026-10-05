.PHONY: test-local stop logs restart test

test-local:
	docker run -d \
		--rm \
		--name homeassistant \
		-v $(shell pwd)/.config:/config \
		-v $(shell pwd)/custom_components:/config/custom_components \
		-p 8123:8123 \
		homeassistant/home-assistant

stop:
	-docker rm -f homeassistant

logs:
	docker logs -f homeassistant

restart: stop test-local

test:
	python3 test.py
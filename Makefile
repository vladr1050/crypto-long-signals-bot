run:
	python -m app.main

deploy:
	git add .
	git commit -m "Deploy update"
	git push origin main

install:
	pip install -r requirements.txt

setup:
	python3.12 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	cp env.example .env
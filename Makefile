run:
	python -m app.main

deploy:
	git add .
	git commit -m "Deploy update"
	git push origin main

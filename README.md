# About
Hey there.

It took me 2,5 working days to perform the task

All source files are located in the repo.

## Set up project
Clone the project
```bash
  git clone https://github.com/kmatek/thumbnails-task.git
```
Go to the project directory
```bash
  cd thumbnail-task
```
Install dependencies
```bash
  docker-compose build
```
Load fixtures
```bash
  docker-compose run --rm app sh -c "python manage.py migrate && python manage.py loaddata fixtures.json"
```
Start project
```bash
  docker-compose up
```
## Documentation route
```bash
127.0.0.1:8000/api/docs
```

# Instructions link
https://londonappdeveloper.com/django-docker-deployment-with-https-using-letsencrypt/   


# Run on production
`docker compose -f docker-compose.deploy.yml up -d`


# After upd app service (django) conteiner (for some reason) should be removed. Run as usual after this. 
docker rm lithops-life-app-1
3
# new-voc-website
## Developer Setup ##
1. Fork and clone this repository
2. Create a Python virtual environment using venv. The specific instructions are different depending on your operating system, and can be found [here](https://docs.python.org/3/library/venv.html)
3. With the virtual environment activated, install dependencies
    ```
    pip install -r requirements.txt
    ```
4. Create the database tables
    ```
    python manage.py migrate
    ```
5. Create a superuser (admin) login
   ```sh
    python manage.py createsuperuser
   ```
   Follow the prompts to set an email and password.

6. Run the development server:
   ```sh
    python manage.py runserver
   ```
   Log in, then check the running terminal for the link to verify your email.

7. Navigate to localhost:8000/admin. <br>

   This is the Django admin site, which lets you manually edit the contents of the database tables.
   
   Now: <br>
       1. Ensure that your superuser email is in Accounts -> email addresses <br>
       2. Add a profile to Membership -> profiles with the same email<br>
       3. Add a member to Membership -> membership<br>
       4. And finally, add the member to Membership -> Execs with priority 1.<br>

8. Navigate to localhost8000/membership/manage-memberships/, search up your super user email, and activate your membership!

## Development ##
For most code changes, the development server will automatically restart to include the updated code. If you have to change anything in a `models.py` file, you will have to migrate the change to the database schema:
```sh
python manage.py makemigrations
python manage.py migrate
```
This will automatically generate a new file in the `migrations` folder of the app whose models you have updated. Ensure to include this file when you commit your change. 
When you deploy the code, you will need to run `python manage.py migrate` to update the production database schema according to the changes in the migration file.

## Deployment ##
To deploy the website to production:
1. Clone this repository onto the remote server
2. Copy `.env.sample` into `.env` and replace the placeholders with real values. For `DJANGO_ALLOWED_HOSTS`, use the URL of the website (probably 'ubc-voc.com'). Ensure that `POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY` are strong passwords.
3. Build the docker container: `docker compose build`
4. Migrate the database `docker compose run web python manage.py migrate`
5. Create a superuser `docker compose run web python manage.py createsuperuser`
6. Collect static files `docker compose run web python manage.py collectstatic`
7. Run the containers: `docker compose up -d` (`-d` detaches the containers from your shell, which is necessary for the website to continue to run when your ssh session ends)
8. Configure the server-wide instance of nginx to serve static and media files, eg:
   ```
   location /static/ {
        proxy_pass http://127.0.0.1:8082/static/;
        proxy_set_header Host $host;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:8082/media/;
        proxy_set_header Host $host;
    }
   ```

## Learn More ##
If you have not worked on a Django project before, understanding the [Model-View-Template architecture](https://docs.djangoproject.com/en/5.2/intro/overview/) will help clarify the file structure of this project
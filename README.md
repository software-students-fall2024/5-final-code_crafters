![Test-ML](https://github.com/software-students-fall2024/5-final-code_crafters/actions/workflows/ml-client.yml/badge.svg)
![Test-Web](https://github.com/software-students-fall2024/5-final-code_crafters/actions/workflows/web-app.yml/badge.svg)
![Test-DB](https://github.com/software-students-fall2024/5-final-code_crafters/actions/workflows/db-service.yml/badge.svg)

# Final Project

# Fitness Tracker

This app is a comprehensive fitness tracker that empowers users at all fitness levels to track user workout progress, create personalized workout plans, log exercise details. The user can speak with the app, which can recognize the user's speech and then search for exercises or edit exercises logs based on the spoken input. Meanwhile, the user can refer to the large language model to generate weekly workout plan based on user profile.

## Prerequisites
Make sure you have the following software installed on your machine:

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Installing Docker
1. Go to the [Docker official website](https://www.docker.com/products/docker-desktop) and download Docker Desktop for your operating system.
2. Follow the installation instructions and ensure Docker Desktop is running.

Here's a refined version of your `.env` file creation instructions for clarity and completeness:

---

## Creating `.env` Files for Your Project

### 1. Web Application - `.env` File for Database Connection
Create an `.env` file in the `web-app` directory to configure the database connection. Add the following content:

```
MONGO_URI="mongodb+srv://<your_username>:<your_password>@cluster0.0yolx.mongodb.net/fitness_db?retryWrites=true&w=majority"
```

- Replace `<your_username>` and `<your_password>` with your actual MongoDB username and password.
- This connection string connects to a MongoDB Atlas cluster. Ensure you have the correct credentials and permissions.

### 2. Machine Learning Client - `.env` File for Google Cloud Service
Create an `.env` file in the `machine-learning-client` directory to configure Google Cloud authentication. Add the following content:

```
GOOGLE_CLOUD_SERVICE_ACCOUNT_JSON='{
  "type": "<your_type>",
  "project_id": "<your_project>",
  "private_key_id": "<your_key_id>",
  "private_key": "<your_key>",
  "client_email": "<your_email>",
  "client_id": "<your_id>",
  "auth_uri": "<your_auth_uri>",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "<your_uri>",
  "universe_domain": "googleapis.com"
}'
```

```
GEMINI_API_KEY = "<your_api_key>"
```

- Replace each `<placeholder>` (e.g., `<your_type>`, `<your_project>`) with the corresponding values from your Google Cloud service account.
- To obtain these values, you need to register a Google Cloud service account and download the JSON key file containing the credentials. Also, you would need to Log in to your Gemini account, navigate to the account settings page, vind the API key management section, create a new API key and ensure it has the appropriate permissions.

## Running the Project with Docker Compose
To build and start the containers, run the following command:

   ```bash
   docker-compose up --build
   ```

   - The `--build` flag ensures images are rebuilt before starting the containers.
   - To run the services in the background (detached mode), you can add the `-d` option:

     ```bash
     docker-compose up -d
     ```

3. Access the application (refer to the port mapping specified in `docker-compose.yml`). For example, you might access it at `http://localhost:5001`. or `http://138.197.83.21:5001`

## Stopping the Services
To stop and remove the containers, networks, and other resources created by `docker-compose up`, use:

```bash
docker-compose down
```

## DockerHub Images

- Web-App: [DockerHub Link](https://hub.docker.com/repository/docker/blackcloudkn/web-app/general)

- Pull the image:
```
docker pull blackcloudkn/web-app:latest
```

- Machine Learning Client: [DockerHub Link](https://hub.docker.com/repository/docker/blackcloudkn/machine-learning-client/general)

- Pull the image:
```
docker pull blackcloudkn/machine-learning-client:latest
```

- MongoDB Database: [DockerHub Link](https://hub.docker.com/repository/docker/blackcloudkn/db-service/general)

- Pull the image:
```
docker pull blackcloudkn/db-service:latest
```

## Setup Virtual Environment Instructions

### 1. Clone the Repository

```
git clone https://github.com/software-students-fall2024/5-final-code_crafters.git
cd 5-final-code_crafters
```

### 2. Go to the directory that you want to set virtual environment for

```
cd web-app
```

or

```
cd machine-learning-client
```

or

```
cd db-service
```

### 3. Install pipenv

```
pip install pipenv
```

### 4. Install dependencies

```
pipenv install
```

### 5. Activate the shell

```
pipenv shell
```
And you can access our Fitness Tracker [Here](http://138.197.83.21:5001)! .

## Team members

* [Alex](https://github.com/alexyujiuqiao)
* [Haoyi](https://github.com/hw2782)
* [Keven](https://github.com/BlackCloud-K)
* [Nicole](https://github.com/niki531)

# Locomotive App

This project is a Flask-based web application designed for managing locomotive operational data and thresholds. It integrates with HashiCorp Vault for secure secrets management and uses PostgreSQL for user data.

---

## Features

- **User Authentication**: Supports user login, registration, and session management using Flask-Login.
- **Secure Secrets Management**: Integrates with HashiCorp Vault for database credentials, thresholds, and certificate management.
- **Dashboard**: Displays locomotive data and operational thresholds.
- **PKI Integration**: Requests and displays certificates from Vault's PKI engine.
- **Health Check**: Provides a simple endpoint for service health monitoring.

---

## Prerequisites

1. Vault up and running and registered in Consul as `vault.service.consul`.
2. PostgreSQL up and running registered in Consul as `postgres.service.consul`.
3. Consul up and running registered in Consul as `consul.service.consul`.
4. Nomad up and running registered in Consul as `nomad.service.consul`.
5. Python 3.12 or later.
6. Docker (optional for containerization).

---

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/locomotive-app.git
    cd locomotive-app
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:
    ```bash
    export VAULT_ADDR="http://localhost:8200"
    export VAULT_TOKEN="your-vault-token"
    export DB_HOST="localhost"
    export DB_PORT="5432"
    ```

4. Configure your PostgreSQL database:
    ```sql
    CREATE DATABASE test;
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    );
    ```

---

## Running the Application

### Locally

1. Start the Flask app:
    ```bash
    python app.py
    ```

2. Access the app in your browser:
    ```
    https://localhost:8080
    ```

### With Docker

1. Build the Docker image:
    ```bash
    docker build -t locomotive-app .
    ```

2. Run the Docker container:
    ```bash
    docker run -p 8080:8080 --env-file .env locomotive-app
    ```

---

## API Endpoints

### `/login`
- **Methods**: `GET`, `POST`
- **Description**: Allows users to log in.

### `/register`
- **Methods**: `GET`, `POST`
- **Description**: Allows users to register.

### `/dashboard`
- **Methods**: `GET`
- **Description**: Displays locomotive operational data and thresholds.

### `/get_certificate`
- **Methods**: `GET`
- **Description**: Requests and displays a certificate from Vault's PKI engine.

### `/logout`
- **Methods**: `GET`
- **Description**: Logs out the current user.

### `/health`
- **Methods**: `GET`
- **Description**: Returns a 200 status code if the app is running.

---

## Vault Integration

- **Secrets Management**:
  - Database credentials are dynamically fetched using Vault's Database Secrets Engine.
  - Thresholds and locomotive data are retrieved from the KV Secrets Engine.

- **PKI**:
  - Certificates are generated using Vault's PKI engine.

---

## Environment Variables

| Variable          | Description                     |
|-------------------|---------------------------------|
| `VAULT_ADDR`      | URL of the Vault server         |
| `VAULT_TOKEN`     | Authentication token for Vault  |
| `DB_HOST`         | PostgreSQL host                 |
| `DB_PORT`         | PostgreSQL port                 |

---

## Deployment with Nomad

Example Nomad Job Configuration:

```hcl
job "locomotive-app" {
  datacenters = ["dc1"]
  type        = "service"

  group "locomotive-app-group" {
    count = 1

    network {
      port "http" {
        to     = 8080
        static = 23762
      }
    }

    task "flask" {
      driver = "docker"
      config {
        image      = "bernardogza83/locomotive-app:latest"
        ports      = ["http"]
        entrypoint = ["python"]
        args       = ["app.py"]
      }

      vault {
        policies = ["locomotive-app-policy"]  # Specify the policy that grants access to secrets
      }

      template {
        data = <<EOH
          {{ with secret "database/creds/my-postgresql-role" }}
          DB_USER="{{ .Data.username }}"
          DB_PASSWORD="{{ .Data.password }}"
          {{ end }}
        EOH
        destination = "secrets/db_env"
        env         = true
      }

      service {
        name = "locomotive-app"
        port = "http"
        tags = ["flask-app"]
        check {
          name     = "flask-app-alive"
          type     = "http"
          interval = "10s"
          timeout  = "2s"
          path     = "/health"  # Ensure you have a health check endpoint in your app
        }
      }

      env = {
        VAULT_ADDR = "http://host.docker.internal:8200"  # Use Consul DNS for Vault address
        DB_HOST    = "host.docker.internal"             # Use Consul DNS for PostgreSQL address
        DB_PORT    = "5432"
        DB_NAME    = "test"
      }

      resources {
        cpu    = 500  # 0.5 CPU
        memory = 512  # 512 MB RAM
      }
    }
  }
}
```
### Postgress Deployment

Example Postgres Job Configuration:

```
job "postgres" {
  datacenters = ["dc1"]

  group "postgres" {
    network {
      port "db" {
        static = 5432
      }
    }

    task "postgres" {
      driver = "docker"
      config {
        image = "postgres:latest"
        ports = ["db"]
      }

      env {
        POSTGRES_PASSWORD = "password123"
        POSTGRES_DB       = "test"
        POSTGRES_USER     = "admin"
      }

      template {
        destination = "/etc/postgresql/postgresql.conf"
        data = <<EOF
            # Modify the port in the postgresql.conf
            port = 5432
            EOF
      }

      service {
        name = "postgres"
        port = "db"
        tags = ["database"]
        check {
          name     = "postgres alive"
          type     = "tcp"
          interval = "10s"
          timeout  = "2s"
        }
      }
    }
  }
}
```
job "locomotive-app" {
  datacenters = ["dc1"]
  type = "service"

  group "locomotive-app-group" {
    count = 1

    network {
      port "http" {
        to = 8080
        static = 23762
      }
    }

    task "flask" {
      driver = "docker"
      config {
        image = "bernardogza83/locomotive-app:latest"
        ports = ["http"]
        # Specify the command and arguments to run the Flask app
        entrypoint = ["python"]
        args = ["app.py"]
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

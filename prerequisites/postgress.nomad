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


# OpenTelemetry Distributed Observability

A comprehensive local development environment for distributed observability using OpenTelemetry, demonstrating best practices for implementing observability in microservices architectures.

## 🚀 Overview

This project sets up a complete observability stack with:
- **4 Sample Applications** - Multiple services for demonstrating distributed tracing
- **OpenTelemetry Collector** - Centralized telemetry collection and processing
- **Prometheus** - Metrics collection and storage
- **Loki** - Log aggregation and analysis
- **Grafana** - Visualization and dashboarding
- **MySQL** - Backend data store for applications

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.8+ (if running apps locally)
- Git

## 🏗️ Project Structure

```
.
├── app01/                          # Sample application 1
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── app02/                          # Sample application 2
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── app03/                          # Sample application 3
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── app04/                          # Sample application 4
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── grafana/                        # Grafana configuration
│   └── provisioning/
│       └── datasources/
│           └── datasources.yml
├── mysql-init/                     # MySQL initialization
│   └── 01-init.sql.sql
├── scripts/                        # Helper scripts
│   ├── start.sh                   # Start all services
│   ├── cleanup.sh                 # Clean up environment
│   └── test-demo.sh               # Run demonstration
├── docker-compose.yml              # Docker Compose configuration
├── otelcol-config.yaml            # OpenTelemetry Collector config
├── prometheus.yml                 # Prometheus configuration
├── loki-config.yaml               # Loki configuration
├── .env                           # Environment variables
└── README.md                      # This file
```

## 🚀 Quick Start

### 1. Clone the Repository

\\\ash
git clone https://github.com/InulaC/OTel-Distributed-Observability.git
cd OTel-Distributed-Observability
\\\

### 2. Start All Services

\\\ash
bash scripts/start.sh
\\\

This will:
- Build and start all Docker containers
- Initialize the database
- Configure data sources in Grafana
- Set up OpenTelemetry collection pipeline

### 3. Access Services

- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Loki**: http://localhost:3100
- **OpenTelemetry Collector**: http://localhost:4317 (gRPC), http://localhost:4318 (HTTP)

#### Grafana Credentials
- Username: dmin
- Password: dmin (or as configured in .env)

### 4. Run the Demo

\\\ash
bash scripts/test-demo.sh
\\\

This will generate sample traffic and demonstrate distributed tracing across the services.

### 5. Cleanup

\\\ash
bash scripts/cleanup.sh
\\\

This will stop and remove all containers.

## 🔧 Configuration

### OpenTelemetry Collector (\otelcol-config.yaml\)

Configures:
- Receivers (gRPC and HTTP)
- Processors (batch processing)
- Exporters (Prometheus, Loki, etc.)

### Prometheus (\prometheus.yml\)

Scrapes metrics from:
- OpenTelemetry Collector
- Application endpoints
- System metrics

### Loki (\loki-config.yaml\)

Log aggregation configuration for all services.

### Environment Variables (\.env\)

Configure:
- Database credentials
- Service ports
- Tracing endpoints
- Log levels

## 📊 Distributed Tracing

Each application is instrumented with OpenTelemetry to:
- Generate spans for requests
- Propagate trace context across services
- Collect performance metrics
- Log structured events

Traces are correlated and viewable in Grafana.

## 📈 Metrics and Dashboards

Pre-configured Grafana dashboards show:
- Request latency and throughput
- Service dependencies
- Error rates
- Resource utilization
- Distributed trace visualization

## 🛠️ Development

### Adding a New Service

1. Create a new app directory with Python application
2. Add OpenTelemetry instrumentation (see \pp01/app.py\ as reference)
3. Update \docker-compose.yml\ with new service
4. Configure OTel Collector to scrape metrics from the new service
5. Add Grafana dashboards as needed

### Sample Application Structure

Each app includes:
- Flask/FastAPI web server
- OpenTelemetry SDK initialization
- Automatic instrumentation
- Custom span creation for business logic

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (\git checkout -b feature/improvement\)
3. Commit your changes (\git commit -am 'Add new feature'\)
4. Push to the branch (\git push origin feature/improvement\)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)

## 🆘 Troubleshooting

### Services won't start
- Ensure Docker is running: \docker ps\
- Check available ports (3000, 4317, 4318, 9090, 3100)
- Review logs: \docker-compose logs\

### No traces appearing in Grafana
- Verify OTel Collector is running: \docker-compose ps\
- Check application logs for instrumentation errors
- Ensure trace sampling is not disabled in app configuration

### Database connection issues
- Verify MySQL container is healthy: \docker-compose ps\
- Check credentials in \.env\ file
- Review mysql initialization script: \mysql-init/01-init.sql.sql\

---

**Last Updated**: March 2026

For more information or issues, please open an issue on GitHub.

# Local Distributed Observability Demo (OpenTelemetry)

## Overview

This project demonstrates a **local distributed observability system** using OpenTelemetry.
It showcases the three pillars of observability:

* **Metrics** (Prometheus + Grafana)
* **Logs** (Loki + Grafana)
* **Traces** (Jaeger + Grafana)

The system consists of multiple microservices communicating over HTTP, with telemetry collected centrally and visualized through Grafana.

---

## Architecture

```
User
 │
 ▼
app03 (orchestrator)
 │
 ├── app04 (dependency check)
 │
 └── app02 (proxy / processing layer)
        │
        └── app01 (data service)
              │
              ▼
            MySQL

app03 → MongoDB
```

### Observability Pipeline

```
All Apps
   │
   ▼
OpenTelemetry Collector
   ├── Prometheus (metrics)
   ├── Loki (logs)
   └── Jaeger (traces)
```

---

## Services

### app01 – Data Service

* Handles user creation and retrieval
* Uses MySQL (`customers_app01`)
* Contains **intentional failure endpoint**:

  * Fails **after DB read** to demonstrate error propagation

---

### app02 – Proxy & Internal Processing

* Acts as an intermediate service between app03 and app01
* Responsibilities:

  * Proxy requests to app01
  * Copy users into `customers_app02`
  * Log proxy events into `proxy_details`
  * Perform **local processing spans**

#### Internal Work (Custom Spans)

app02 includes **manual spans** to simulate internal processing:

* preprocessing delay
* file write simulation
* processing delay

These spans are created using OpenTelemetry Python API (no external services required).

---

### app03 – Orchestrator

* Calls app04 for dependency validation
* Calls app02 for user retrieval
* Stores results in MongoDB (`received_customers`)
* Provides:

  * Normal flow (`/fetch-and-store`)
  * Failure flow (`/fetch-and-store-then-fail`)

---

### app04 – Dependency Service

* Simple health-check service
* Randomly fails to simulate dependency issues

---

## Databases

### MySQL

Tables:

* `customers_app01`
* `customers_app02`
* `proxy_details`

`proxy_details` is used to log proxy events in app02:

```sql
CREATE TABLE IF NOT EXISTS proxy_details (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_endpoint VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### MongoDB

Collection:

* `received_customers` (used by app03)

---

## Observability Stack

| Component      | Purpose             | Port        |
| -------------- | ------------------- | ----------- |
| Grafana        | Visualization       | 3000        |
| Prometheus     | Metrics storage     | 9090        |
| Loki           | Log storage         | 3100        |
| Jaeger         | Trace visualization | 16686       |
| OTEL Collector | Telemetry pipeline  | 4317 / 4318 |

---

## Key Features

### 1. Distributed Tracing

Tracks requests across:

* app03 → app02 → app01 → MySQL
* app03 → MongoDB

---

### 2. Failure After DB Retrieval

Special endpoint demonstrates:

* successful DB query
* failure after data retrieval
* error propagation across services

Trace example:

```
app03
 └── app02
      └── app01
           └── MySQL SELECT
           ✖ failure after DB read
```

---

### 3. Internal Processing in app02

app02 generates additional spans using manual instrumentation:

```
app02
 ├── local_preprocess
 ├── file_write_simulation
 └── processing_delay
```

This demonstrates:

* custom span creation
* internal service visibility

---

### 4. Proxy Event Logging (app02)

Each proxy call logs an event into MySQL:

* endpoint accessed
* timestamp

This creates additional **database spans inside app02**, enriching traces.

---

### 5. Logs

* Structured JSON logs
* Stored in `/var/log/demo/*.jsonl`
* Collected via OTEL `filelog` receiver
* Visualized in Grafana (Loki)

---

### 6. Metrics

Includes:

* HTTP request rate
* latency
* error rates
* system and container metrics

---

## Running the Project

### 1. Build and start services

```bash
docker compose down -v
docker compose up --build
```

---

### 2. Access dashboards

* Grafana: http://localhost:3000
* Jaeger: http://localhost:16686
* Prometheus: http://localhost:9090

---

### 3. Generate traffic

Run the traffic generator:

```bash
bash testdemo.sh
```

---

## Important Endpoints

### app03

* `/fetch-and-store/<id>` → normal flow
* `/fetch-and-store-then-fail/<id>` → failure after DB

### app02

* `/proxy-user/<id>`
* `/proxy-user-then-fail/<id>`
* `/copy-user/<id>`

### app01

* `/get-user/<id>`
* `/get-user-then-fail/<id>`
* `/create-user`

---

## Demo Highlights

During the demo, you can show:

1. **Full request trace across services**
2. **Failure propagation after DB read**
3. **Internal spans in app02**
4. **Database spans in multiple services**
5. **Logs correlated with traces**
6. **Metrics in Grafana**

---

## Key Learning Points

* Difference between **auto-instrumentation vs manual spans**
* How **distributed tracing works across services**
* Importance of **context propagation**
* Observability across:

  * application layer
  * database layer
  * infrastructure layer

---

## Future Improvements

* Parallel service calls
* Alerting rules in Grafana
* Service dependency graph
* Load testing integration
* Cross-team tracing simulation

---

## Author

Developed as a **local OpenTelemetry observability demo** for distributed systems learning and presentation.

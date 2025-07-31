# Azure Application Insights Integration

This document describes how to configure and use Azure Application Insights instrumentation in the ARC2 Server for comprehensive observability and performance monitoring.

## Overview

The ARC2 Server now includes OpenTelemetry-based instrumentation that automatically captures and sends telemetry data to Azure Application Insights, providing:

- **HTTP request/response tracing** for FastAPI endpoints
- **External API call monitoring** for requests to Gemini, OpenAI, and KM APIs
- **Database operation tracking** for DynamoDB queries
- **Azure Storage operation monitoring** for TTS caching
- **Custom business logic tracing** with detailed attributes

## Configuration

### 1. Azure Application Insights Setup

1. Create an Application Insights resource in Azure Portal
2. Copy the connection string from the resource overview page
3. Add the connection string to your environment configuration

### 2. Environment Configuration

Add the Application Insights connection string to your `.env` file:

```bash
# Azure Application Insights Settings
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=00000000-0000-0000-0000-000000000000;IngestionEndpoint=https://your-region.in.applicationinsights.azure.com/;LiveEndpoint=https://your-region.livediagnostics.monitor.azure.com/
```

**Note:** The instrumentation will gracefully disable itself if no connection string is provided, so the application will continue to work normally in development environments.

### 3. Dependencies Installation

The required OpenTelemetry packages are included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Features

### Automatic Instrumentation

The following components are automatically instrumented without code changes:

- **FastAPI endpoints**: All HTTP requests are traced with status codes, response times, and error details
- **External HTTP requests**: All outbound requests via the `requests` library are captured
- **AWS DynamoDB**: Operations through boto3 are automatically tracked

### Custom Instrumentation

Additional custom spans are added for detailed tracking:

#### DynamoDB Operations
- Operation type (get_item, put_item, query, scan, etc.)
- Table name and AWS region
- Key information (sanitized)
- Item sizes and result counts
- Error codes and exception details

#### Azure Storage Operations
- Blob container and blob names
- Upload/download operation details
- File sizes and transfer metrics
- Success/failure status

#### Request Flow Tracing
Custom spans can be added throughout the application using the telemetry utilities:

```python
from src.telemetry import telemetry_span, add_span_attributes

# Context manager for automatic span handling
with telemetry_span("custom.operation", {"user_id": "123", "org_id": "456"}) as span:
    # Your business logic here
    result = perform_operation()
    add_span_attributes(span, result_count=len(result))
```

## Usage Examples

### Viewing Telemetry in Azure Portal

1. Navigate to your Application Insights resource in Azure Portal
2. Use the following features:

#### Application Map
- Visualize dependencies between your app and external services
- See call volumes and response times between components

#### Performance
- View endpoint response times and throughput
- Identify slow operations and bottlenecks
- Monitor DynamoDB and Azure Storage performance

#### Failures
- Track HTTP errors and exceptions
- Identify failing API calls or database operations
- View detailed error traces with stack traces

#### Live Metrics
- Real-time monitoring of requests and performance
- Monitor active server instances
- See live error rates and response times

### Custom Queries (KQL)

Use Application Insights' powerful query language to analyze your data:

```kql
// View all DynamoDB operations
dependencies
| where type == "DynamoDB"
| summarize count(), avg(duration) by name, bin(timestamp, 5m)

// Monitor API response times
requests
| where url contains "/api/v1/answer-sse"
| summarize avg(duration), count() by bin(timestamp, 1h)

// Track external API failures
dependencies
| where success == false
| where type in ("OpenAI", "Gemini", "KM")
| summarize count() by name, resultCode
```

### Setting Up Alerts

Create alerts in Azure Portal for:

- High error rates on critical endpoints
- Slow DynamoDB operations
- Failed external API calls
- High memory or CPU usage

## Troubleshooting

### Telemetry Not Appearing

1. **Check connection string**: Verify the `APPLICATIONINSIGHTS_CONNECTION_STRING` is correctly set
2. **Check logs**: Look for telemetry initialization messages in application logs
3. **Verify network**: Ensure the application can reach Azure endpoints
4. **Check sampling**: Data might be sampled; wait a few minutes for data to appear

### Performance Impact

The OpenTelemetry instrumentation is designed for minimal performance impact:

- Spans are batched and sent asynchronously
- Sampling can be configured to reduce volume
- Instrumentation can be completely disabled by removing the connection string

### Development vs Production

- **Development**: Leave `APPLICATIONINSIGHTS_CONNECTION_STRING` empty to disable telemetry
- **Production**: Always configure Application Insights for full observability

## Architecture

### Components

1. **src/telemetry.py**: Core telemetry configuration and utilities
2. **OpenTelemetry Auto-instrumentation**: Handles FastAPI and requests automatically
3. **Custom Spans**: Added to DynamoDB and Azure Storage handlers
4. **Azure Monitor Exporter**: Sends data to Application Insights

### Data Flow

```
Application Code
    ↓
OpenTelemetry SDK
    ↓
Batch Span Processor
    ↓
Azure Monitor Exporter
    ↓
Azure Application Insights
```

## Best Practices

1. **Use meaningful span names**: Choose descriptive names for custom operations
2. **Add relevant attributes**: Include user IDs, organization IDs, and other contextual data
3. **Handle exceptions**: Use `record_exception()` to capture error details
4. **Monitor costs**: Application Insights charges by data volume; consider sampling for high-traffic applications
5. **Use structured logging**: Complement telemetry with structured application logs

## Security Considerations

- Connection strings contain sensitive information; store them securely
- Avoid logging sensitive data in span attributes
- Consider data retention policies in Application Insights
- Review what data is being sent to ensure compliance requirements

## Support

For issues with Application Insights integration:

1. Check the application logs for telemetry-related messages
2. Verify Azure Application Insights resource configuration
3. Review network connectivity and firewall settings
4. Consult Azure Application Insights documentation for advanced configuration
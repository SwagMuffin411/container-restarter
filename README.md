# Container Restarter

A Python-based Docker container that automatically restarts a specified Docker container at a configured time via the Portainer API.

## Features

- Restart any Docker container at a scheduled time
- Configurable via environment variables
- Supports both Portainer API Key and Username/Password authentication
- Runs as a Docker container itself
- Automatic JWT token refresh for long-running operations
- Detailed logging

## Prerequisites

- Docker installed
- Portainer instance running and accessible
- Portainer API key or admin credentials

## Quick Start

### 1. Get Your Portainer API Key

To create an API key in Portainer:

1. Log in to Portainer
2. Go to **User settings** (click your username in the top right)
3. Scroll to **Access tokens**
4. Click **Add access token**
5. Give it a description and click **Create**
6. Copy the API key (you won't be able to see it again!)

### 2. Configure Environment Variables

Edit the `docker-compose.yml` file and set your configuration:

```yaml
environment:
  PORTAINER_URL: "http://your-portainer:9000"
  PORTAINER_API_KEY: "ptr_your-api-key-here"
  ENDPOINT_ID: "1"
  CONTAINER_NAME: "your-container-name"
  RESTART_TIME: "03:00"
  CHECK_INTERVAL: "60"
```

### 3. Build and Run

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

## Configuration

All configuration is done via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORTAINER_URL` | Yes | - | URL of your Portainer instance (e.g., `http://portainer:9000`) |
| `PORTAINER_API_KEY` | Yes* | - | Portainer API access token (preferred authentication method) |
| `PORTAINER_USERNAME` | Yes* | - | Portainer admin username (alternative to API key) |
| `PORTAINER_PASSWORD` | Yes* | - | Portainer admin password (alternative to API key) |
| `ENDPOINT_ID` | No | `1` | Portainer endpoint ID (usually `1` for local Docker) |
| `CONTAINER_NAME` | Yes | - | Name or ID of the container to restart |
| `RESTART_TIME` | No | `03:00` | Time to restart in 24-hour format (HH:MM) |
| `CHECK_INTERVAL` | No | `60` | How often to check the time in seconds |

*Either `PORTAINER_API_KEY` OR both `PORTAINER_USERNAME` and `PORTAINER_PASSWORD` must be provided.

## Examples

### Using API Key (Recommended)

```yaml
environment:
  PORTAINER_URL: "http://192.168.1.100:9000"
  PORTAINER_API_KEY: "ptr_abcdef123456"
  CONTAINER_NAME: "nginx"
  RESTART_TIME: "02:30"
```

### Using Username/Password

```yaml
environment:
  PORTAINER_URL: "https://portainer.example.com"
  PORTAINER_USERNAME: "admin"
  PORTAINER_PASSWORD: "your-secure-password"
  CONTAINER_NAME: "my-app"
  RESTART_TIME: "04:00"
```

### Using Container ID Instead of Name

```yaml
environment:
  PORTAINER_URL: "http://portainer:9000"
  PORTAINER_API_KEY: "ptr_key123"
  CONTAINER_NAME: "a1b2c3d4e5f6"  # First 12 chars of container ID
  RESTART_TIME: "23:59"
```

## Running Without Docker Compose

You can also run the container directly with `docker run`:

```bash
docker build -t container-restarter .

docker run -d \
  --name container-restarter \
  --restart unless-stopped \
  -e PORTAINER_URL="http://portainer:9000" \
  -e PORTAINER_API_KEY="ptr_your-api-key" \
  -e CONTAINER_NAME="nginx" \
  -e RESTART_TIME="03:00" \
  container-restarter
```

## Finding Your Endpoint ID

Most installations use endpoint ID `1` for the local Docker environment. To verify:

1. Log in to Portainer
2. Go to **Environments**
3. Your endpoint ID is shown in the list

## Timezone Considerations

The container uses UTC time by default. To use your local timezone:

**Option 1**: Specify time in UTC

```yaml
RESTART_TIME: "03:00"  # This is 03:00 UTC
```

**Option 2**: Mount local timezone file

```yaml
volumes:
  - /etc/localtime:/etc/localtime:ro
```

**Option 3**: Set TZ environment variable

```yaml
environment:
  TZ: "America/New_York"
```

## Logging

The container logs all operations. View logs with:

```bash
docker-compose logs -f
```

Expected output:
```
2026-01-27 03:00:00 - INFO - Time to restart container nginx
2026-01-27 03:00:01 - INFO - Successfully restarted container a1b2c3d4e5f6
2026-01-27 03:00:01 - INFO - Next restart scheduled for 03:00 tomorrow
```

## Troubleshooting

### Container not found

**Error**: `Container 'myapp' not found`

**Solution**: Make sure the container name matches exactly. Container names in Docker start with `/`, so both `myapp` and `/myapp` should work. You can also use the container ID.

### Authentication failed

**Error**: `Authentication failed: 401`

**Solution**:
- Verify your API key is correct and hasn't expired
- Check that your username/password are correct
- Ensure you have admin privileges in Portainer

### Connection refused

**Error**: `Failed to restart container: Connection refused`

**Solution**:
- Verify `PORTAINER_URL` is correct and accessible from the container
- If using `localhost` or `127.0.0.1`, change to your host IP or `host.docker.internal`
- Check that Portainer is running

### Wrong time

**Issue**: Container restarts at wrong time

**Solution**:
- Check your timezone settings
- Verify `RESTART_TIME` is in 24-hour format (HH:MM)
- Consider using UTC time or mounting timezone file

## API Reference

This tool uses the following Portainer API endpoints:

- `POST /api/auth` - Authenticate and get JWT token
- `GET /api/endpoints/{id}/docker/containers/json` - List containers
- `POST /api/endpoints/{id}/docker/containers/{id}/restart` - Restart container

For more information, see:
- [Portainer API Documentation](https://docs.portainer.io/api/docs)
- [API Usage Examples](https://docs.portainer.io/api/examples)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

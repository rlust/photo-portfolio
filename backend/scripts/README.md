# Database Administration Scripts

This directory contains scripts to help manage the Photo Portfolio application's database and deployment.

## Scripts

### `cloud-sql-proxy.sh`

A script to easily manage the Cloud SQL Proxy for local development.

#### Features:
- Start/stop the Cloud SQL Proxy
- Automatic installation of Cloud SQL Proxy if not found
- Support for custom ports and credentials
- Automatic cleanup on exit

#### Usage:
```bash
# Start the proxy
./cloud-sql-proxy.sh -p PROJECT_ID -i INSTANCE_NAME [-r REGION] [-P PORT] [-c CREDENTIALS_FILE]

# Stop the proxy
./cloud-sql-proxy.sh --stop

# Show help
./cloud-sql-proxy.sh --help
```

### `db-admin.sh`

A comprehensive database administration tool for the Photo Portfolio application.

#### Features:
- Database migrations
- Photo reindexing
- Database connection
- Database dump and restore
- Database reset
- Support for both local and Cloud SQL databases

#### Usage:
```bash
# Run database migrations
./db-admin.sh migrate -p PROJECT_ID -i INSTANCE_NAME [options]

# Reindex photos in Google Cloud Storage
./db-admin.sh reindex -p PROJECT_ID -i INSTANCE_NAME [options]

# Connect to the database
./db-admin.sh connect -p PROJECT_ID -i INSTANCE_NAME [options]

# Create a database dump
./db-admin.sh dump -p PROJECT_ID -i INSTANCE_NAME [options] [output_file]

# Restore a database from a dump
./db-admin.sh restore -p PROJECT_ID -i INSTANCE_NAME [options] input_file

# Reset the database (drop and recreate)
./db-admin.sh reset -p PROJECT_ID -i INSTANCE_NAME [options]

# Show help
./db-admin.sh --help
```

## Prerequisites

1. **Google Cloud SDK**
   - Install from: https://cloud.google.com/sdk/docs/install
   - Run `gcloud init` to authenticate and set up your project

2. **Cloud SQL Proxy**
   - Will be automatically installed if not found
   - Or install manually: https://cloud.google.com/sql/docs/postgres/connect-admin-proxy

3. **PostgreSQL Client Tools**
   - `psql`, `pg_dump`, `pg_restore`
   - On macOS: `brew install postgresql`
   - On Ubuntu: `sudo apt-get install postgresql-client`

## Environment Variables

You can set the following environment variables in a `.env` file or pass them as command-line arguments:

```
# Required for remote connections
PROJECT_ID=your-project-id
DB_INSTANCE=your-db-instance
DB_NAME=photo_portfolio
DB_USER=postgres
DB_PASSWORD=your-db-password

# Optional
REGION=us-central1
SERVICE_NAME=photo-portfolio-backend
LOCAL_PORT=5432
```

## Examples

### Local Development

1. Start the Cloud SQL Proxy:
   ```bash
   ./cloud-sql-proxy.sh -p your-project-id -i your-db-instance
   ```

2. Run database migrations:
   ```bash
   ./db-admin.sh migrate -p your-project-id -i your-db-instance
   ```

3. Connect to the database:
   ```bash
   ./db-admin.sh connect -p your-project-id -i your-db-instance
   ```

### Production

1. Reindex photos in production:
   ```bash
   ./db-admin.sh reindex -p your-project-id -i your-db-instance
   ```

2. Create a database backup:
   ```bash
   ./db-admin.sh dump -p your-project-id -i your-db-instance backup_$(date +%Y%m%d).sql
   ```

3. Reset the database (be careful!):
   ```bash
   ./db-admin.sh reset -p your-project-id -i your-db-instance
   ```

## Troubleshooting

### Cloud SQL Proxy Connection Issues
- Make sure you have the `Cloud SQL Admin API` enabled in your Google Cloud project
- Verify that your user has the `Cloud SQL Client` role
- Check that the Cloud SQL instance exists in the specified region

### Database Connection Issues
- Verify that the Cloud SQL Proxy is running and accessible
- Check that the database user has the correct permissions
- Make sure the database exists and is accessible

### Reindexing Issues
- Verify that the Cloud Run service has the necessary IAM permissions for Cloud Storage
- Check the Cloud Run service logs for any errors
- Make sure the `GCS_BUCKET` environment variable is set correctly

## Security Considerations

- Never commit sensitive information like passwords or API keys to version control
- Use environment variables or a `.env` file (add it to `.gitignore`)
- Regularly rotate database passwords and API keys
- Follow the principle of least privilege when assigning IAM roles

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

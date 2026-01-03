#!/bin/zsh

# Generate a random password
DB_PASSWORD=$(openssl rand -base64 16)
DB_NAME="grandpa"
DB_USER="grandpa"
DB_HOST="localhost"
DB_PORT="5432"

echo "Generating configuration..."

# SQL Commands
# We try to connect to 'postgres' database to create users/dbs.
# We attempt as current user, then as 'postgres' user via sudo.

run_psql() {
    local cmd="$1"
    local db="${2:-postgres}"
    
    # Try as current user
    if psql -d "$db" -c "$cmd" 2>/dev/null; then
        return 0
    fi
    
    # Try with sudo -u postgres
    if command -v sudo >/dev/null; then
        echo "Requesting sudo access to run psql as postgres user..."
        if sudo -u postgres psql -d "$db" -c "$cmd"; then
            return 0
        fi
    fi
    
    return 1
}

echo "Setting up PostgreSQL user and database..."

# Create User
# We use a block to handle "already exists" gracefully if possible, or just ignore error
# But simpler: TRY CREATE, if fails, TRY ALTER.
if ! run_psql "CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';"; then
    echo "User creation failed or user exists. Attempting to update password..."
    if ! run_psql "ALTER USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD';"; then
        echo "Failed to create or update user '$DB_USER'. Please ensure PostgreSQL is running and you have permissions."
        exit 1
    fi
fi

# Create Database
if ! run_psql "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"; then
    echo "Database creation failed or database exists. Proceeding..."
fi

# Grant privileges
run_psql "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO \"$DB_USER\";"

# Grant schema permissions (crucial for PG 15+)
# This needs to run on the specific database
if ! run_psql "GRANT ALL ON SCHEMA public TO \"$DB_USER\";" "$DB_NAME"; then
     # Might fail if we can't connect to the new DB yet, but usually owner can.
     echo "Note: Could not grant schema permissions. If using PG 15+, you might need manual intervention."
fi

echo "Database operations attempted."

# Write to .env
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
fi

update_env() {
    local key=$1
    local val=$2
    # Escape special characters in value if needed (basic handling)
    if grep -q "^$key=" "$ENV_FILE"; then
        # macOS sed requires empty string for -i extension
        sed -i '' "s|^$key=.*|$key=$val|" "$ENV_FILE"
    else
        echo "$key=$val" >> "$ENV_FILE"
    fi
}

echo "Updating .env file..."
update_env "DB_NAME" "$DB_NAME"
update_env "DB_USER" "$DB_USER"
update_env "DB_PASSWORD" "$DB_PASSWORD"
update_env "DB_HOST" "$DB_HOST"
update_env "DB_PORT" "$DB_PORT"

echo "Success! Database configured and credentials stored in .env"


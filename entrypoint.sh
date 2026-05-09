#!/bin/bash
set -e

echo "🔧 Waiting for database to be ready..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "✅ Database is ready"

echo "🧹 Clearing Python cache for reliable reloads..."
find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find /app -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Cache cleared"

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "📋 Running migrations..."
  python manage.py migrate --noinput

  echo "📦 Loading sample data..."
  python manage.py load_sample_data || echo "⚠️  Sample data already loaded"

  echo "👤 Creating admin user (root/9999)..."
  python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='root').exists():
    User.objects.create_superuser('root', 'admin@talenhire.com', '9999')
    print("✅ Admin user created: root/9999")
else:
    print("⚠️  Admin user already exists")
EOF
else
  echo "⏭️  Skipping migrations (RUN_MIGRATIONS != true). Waiting for migrator..."
  until python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'talent_hire.settings')
django.setup()
from django.db.migrations.executor import MigrationExecutor
from django.db import connections
ex = MigrationExecutor(connections['default'])
plan = ex.migration_plan(ex.loader.graph.leaf_nodes())
exit(0 if not plan else 1)
" 2>/dev/null; do
    echo "   ...waiting for migrations to finish"
    sleep 2
  done
  echo "✅ Migrations done"
fi

echo "🚀 Starting application..."
exec "$@"

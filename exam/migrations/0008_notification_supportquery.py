from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exam', '0007_exam_examattempt_exam_question_exam'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('category', models.CharField(
                    choices=[
                        ('info', 'Info'),
                        ('success', 'Success'),
                        ('warning', 'Warning'),
                        ('exam', 'Exam'),
                        ('results', 'Results'),
                        ('support', 'Support'),
                    ],
                    default='info', max_length=20)),
                ('link', models.CharField(blank=True, default='', max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('candidate', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to='exam.candidate')),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SupportQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('status', models.CharField(
                    choices=[
                        ('Open', 'Open'),
                        ('Answered', 'Answered'),
                        ('Closed', 'Closed'),
                    ],
                    default='Open', max_length=20)),
                ('admin_response', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('candidate', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='queries',
                    to='exam.candidate')),
            ],
            options={
                'verbose_name': 'Support Query',
                'verbose_name_plural': 'Support Queries',
                'ordering': ['-created_at'],
            },
        ),
    ]

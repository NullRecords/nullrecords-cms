# Generated by Django 3.2.14 on 2023-01-23 17:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0066_collection_management_permissions'),
        ('home', '0003_artpge_livestreampage_livestreamukrainepage'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContactMail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('inquiry', models.CharField(blank=True, max_length=255)),
                ('message', models.TextField(blank=True)),
                ('email', models.CharField(blank=True, max_length=255)),
                ('file', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255)),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('edit_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Portfolio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('catagory', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
                ('image_logo', models.FileField(blank=True, null=True, upload_to='uploads')),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('edit_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PortfolioItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('catagory', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='uploads')),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('edit_date', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('type', models.CharField(blank=True, max_length=255, null=True)),
                ('catagory', models.CharField(blank=True, max_length=255, null=True)),
                ('url', models.CharField(blank=True, max_length=255, null=True)),
                ('source', models.CharField(blank=True, max_length=255, null=True)),
                ('create_date', models.DateTimeField(blank=True, null=True)),
                ('edit_date', models.DateTimeField(blank=True, null=True)),
                ('portfolio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='home.portfolio')),
            ],
        ),
    ]

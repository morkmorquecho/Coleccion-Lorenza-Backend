from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0006_blog_content_en_blog_content_es_blog_slug_en_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='title',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='blog',
            name='slug',
            field=models.SlugField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='blog',
            name='content',
            field=models.TextField(null=True, blank=True),
        ),
    ]
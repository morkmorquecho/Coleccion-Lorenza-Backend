from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='recipient_name',
            field=models.CharField(
                max_length=200,
                default=''
            ),
        ),
    ]

# pieces/migrations/0005_seed_external_reviews.py

from django.db import migrations
from datetime import datetime
import pytz


def make_dt(year, month, day):
    return datetime(year, month, day, tzinfo=pytz.UTC)


def seed_reviews(apps, schema_editor):
    Review = apps.get_model('pieces', 'Review')

    reviews_data = [
        {
            'external_author': 'Kristina',
            'comment': 'Beautiful Catrina, well crafted and exceeded my expectations. What I like about this piece is is that it\'s whimsical. It\'s a very happy Skelton and it\'s not overly sexy. She looks like how the girl next door would look if she were a Skelton in the after world. An everyday girl. I paired her with another Catrina which is I bought from the seller a year ago. They look like two teen friends. I could see them sitting together on a wall at the beach watching the Skelton boys play volleyball and talking about what Skelton guy was the most handsome and who they hoped would ask them to the Skelton dance. I associate the white bones as a blond and the darker Skelton as a brunette. I plan to use them on a community altar at an Agency that serves families and children because they look like everyday people if they were skeletons.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 10, 10),
            'link_etsy': None,
        },
        {
            'external_author': 'Brian',
            'comment': 'Esta fue una pieza personalizada. Me comuniqué con la artista y conversamos sobre la inspiración y varias ideas de diseño. Tras la colaboración en el concepto de diseño, lo dejé todo en sus manos, y ella creó una pieza aún más dinámica y expresiva de lo que había imaginado. Ha sido un placer trabajar con ella, ¡y estoy muy contento con mi alebrije!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 10, 6),
            'link_etsy': 'https://www.etsy.com/mx/listing/1492694279/alebrije-alacran-de-brian',
        },
        {
            'external_author': 'Kristina',
            'comment': 'I really like this piece, i bought it to go with another piece from this same artist to be displayed at my sweetheart table at my wedding. As usually, the piece is well crafted and beautifully painted.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 8, 1),
            'link_etsy': 'https://www.etsy.com/mx/listing/1465121029/perro-alebrije-montado-en-caballo-a',
        },
        {
            'external_author': 'Kristina',
            'comment': 'Another beautiful, magical masterpiece. The attention to detail and the vibrant colors bring this piece to life. I like that the devil can be taken on and off the bull- so its actually 2 pieces that work together.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2024, 8, 1),
            'link_etsy': 'https://www.etsy.com/mx/listing/1834832471/alebrije-mexicano-diabla-y-toro',
        },
        {
            'external_author': 'Samantha',
            'comment': 'Absolutely thrilled with my purchase! The vendor was incredibly communicative throughout the entire process, keeping me updated on the status of my order. My item arrived much quicker than I expected and was packed with great care to ensure it was safe during transit. When I unwrapped it, I was even more amazed—it\'s *stunning* in person, even more beautiful than the pictures. Highly recommend this shop for anyone looking for quality art and excellent customer service!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 2, 4),
            'link_etsy': 'https://www.etsy.com/mx/listing/1827816140/alebrije-mexicano-diabla-y-caballo',
        },
        {
            'external_author': 'Dominique',
            'comment': 'Great seller!!! Item was perfect!! Excellent packaging and fast shipping!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 1, 13),
            'link_etsy': 'https://www.etsy.com/mx/listing/1451188337/caballo-y-loba-alebrije-regalo-cultural',
        },
        {
            'external_author': 'Danielle',
            'comment': 'I love this calavera so much! It is beautiful. The skill and talent to make such an exquisite one of a kind piece was obvious the moment I took it out of its well packaged box. Honored to have this piece as part of my Mexican folk art collection.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2025, 1, 2),
            'link_etsy': 'https://www.etsy.com/mx/listing/1523348982/esqueleto-de-papel-mache-de-colores-con',
        },
        {
            'external_author': 'Lisa',
            'comment': 'Please let me know when you have another made so I can purchase it! I am in love!!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2024, 12, 28),
            'link_etsy': 'https://www.etsy.com/mx/listing/1846030749/angel-querubin-de-papel-mache-angel',
        },
        {
            'external_author': 'Carolina',
            'comment': 'My alebrije is amazing. Thank you, Lorenza!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2024, 12, 16),
            'link_etsy': 'https://www.etsy.com/mx/listing/1717937649/alebrije-mexicano-de-papel-mache-arte',
        },
        {
            'external_author': 'Teresa',
            'comment': 'The Diablo del Mar y el Cielo is more beautiful than what was pictured! The piece came carefully packaged. It included a certificate of authenticity, a brief history, and a thank you note from Lorenza. I am so happy with this purchase and will definitely purchase from this shop again!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2024, 12, 8),
            'link_etsy': 'https://www.etsy.com/mx/listing/1834358207/alebrije-mexicano-diablo-del-mar-y-el',
        },
        {
            'external_author': 'Debbie',
            'comment': 'I got this piece for my husband for our 1st anniversary. He loved it so much! This papier-mâché golfer is so detailed and looks absolutely perfect in our home! The seller was beyond amazing!! Very responsive, so helpful, and extremely sweet! I will definitely be ordering from them again!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2023, 6, 29),
            'link_etsy': 'https://www.etsy.com/mx/listing/1081738120/esqueleto-golfista-de-papel-mache-del',
        },
        {
            'external_author': 'Maria',
            'comment': 'Just love this little devil so much. The delivery, and updated information from the seller was fast. Thank you for my new little art piece.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2023, 3, 20),
            'link_etsy': 'https://www.etsy.com/mx/listing/1369168345/diablo-alebrije-mexicano-de-papel-mache',
        },
        {
            'external_author': 'Angela',
            'comment': 'La escultura era hermosa y estaba empaquetada digna de gran cuidado. El vendedor mantuvo una gran comunicación y llegó justo cuando anunciaron.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 12, 13),
            'link_etsy': None,
        },
        {
            'external_author': 'Robin',
            'comment': 'Las vibrantes máscaras expresivas llegaron justo a tiempo para la temporada de Samhain y Day Of The Dead. Muy contento con el tiempo y la energía que pones en tu arte. ¡Gracias!',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 9, 23),
            'link_etsy': None,
        },
        {
            'external_author': 'Robin',
            'comment': '¡Mi jaguar es maravilloso! Estamos muy contentos de que viva en nuestra casa. Nos encanta. Gracias por la gran caja en la que pusiste todo, la guardamos y gracias por el regalo también. Maravilloso arte vibrante bien hecho. Estoy agradecido de haberte encontrado.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2023, 9, 23),
            'link_etsy': 'https://www.etsy.com/mx/listing/1100726309/mascara-grande-de-jaguar-de-papel-mache',
        },
        {
            'external_author': 'Gissele',
            'comment': 'Estoy completamente enamorado de este charro y su amigo 😍 toro ¡Se ven aún mejor en persona! Es una pieza muy divertida de mostrar. Esta es mi tercera compra y puedo decir que la calidad es consistente. Este artista se comunica durante todo el proceso y el envío fue extremadamente rápido. Estoy muy feliz de apoyar a una artista que realmente captura la cultura mexicana con su arte vivo e imaginativo.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 7, 22),
            'link_etsy': 'https://www.etsy.com/mx/listing/1177612357/toro-y-charro-articulado-con-sombrero',
        },
        {
            'external_author': 'Gisselle',
            'comment': 'Esta hermosa obra de arte es mi 2ª compra de este vendedor. La artesanía, desde la escultura hasta los colores y la expresión, es realmente espectacular. Gracias Lorenza por poner tanto orgullo en tu trabajo 😊',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 6, 17),
            'link_etsy': 'https://www.etsy.com/mx/listing/1112564758/esqueleto-y-cactus-de-papel-mache-con',
        },
        {
            'external_author': 'Sonia',
            'comment': '¡¡ASOMBROSO!!! Esta es mi 2ª compra de este artista talentoso y creativo. Máscara bien elaborada, hábilmente pintada, audazmente diseñada y llena de significado cultural. El vendedor / artista es súper amigable, el envío es rápido y los artículos se empacan con cuidado en cajas personalizadas. No puedo esperar a que lo cuelgue como punto focal en mi habitación :)',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 3, 11),
            'link_etsy': 'https://www.etsy.com/mx/listing/1099193377/mascara-de-guerrero-jaguar-de-papel',
        },
        {
            'external_author': 'Sonia',
            'comment': 'AMOR AMOR AMOR esta pieza !!! Una expresión tan alegre en esta pieza bellamente diseñada y elaborada, claramente hecha con pasión y cuidado. El vendedor / artista es extremadamente servicial y amable, el envío fue rápido. La caja personalizada y el regalo extra son muy apreciados, muy amables y atentos. Esperamos futuras compras de este artista creativo, apasionado y verdaderamente talentoso.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 2, 22),
            'link_etsy': 'https://www.etsy.com/mx/listing/1154964988/esqueleto-con-mariposa-monarca-de-papel',
        },
        {
            'external_author': 'Sonia',
            'comment': 'AMOR AMOR AMOR esta pieza !!! Una expresión tan alegre en esta pieza bellamente diseñada y elaborada, claramente hecha con pasión y cuidado. El vendedor / artista es extremadamente servicial y amable, el envío fue rápido. La caja personalizada y el regalo extra son muy apreciados, muy amables y atentos. Esperamos futuras compras de este artista creativo, apasionado y verdaderamente talentoso.',
            'rating': 5,
            'review_type': 'external',
            'created_at': make_dt(2022, 2, 22),
            'link_etsy': 'https://www.etsy.com/mx/listing/1791443353/catrina-de-gran-tamano-arte-de-papel',
        },
    ]

    created_count = 0
    for data in reviews_data:
        created_at = data.pop('created_at')
        obj, created = Review.objects.get_or_create(
            external_author=data['external_author'],
            comment=data['comment'],
            defaults={
                'rating': data['rating'],
                'review_type': data['review_type'],
                'link_etsy': data.get('link_etsy'),
            }
        )
        if created:
            Review.objects.filter(pk=obj.pk).update(created_at=created_at)
            created_count += 1

    print(f"Se crearon {created_count} reseñas externas")


def unseed_reviews(apps, schema_editor):
    Review = apps.get_model('pieces', 'Review')

    authors = [
        'Kristina', 'Brian', 'Samantha', 'Dominique', 'Danielle',
        'Lisa', 'Carolina', 'Teresa', 'Debbie', 'Maria', 'Angela',
        'Robin', 'Gissele', 'Gisselle', 'Sonia',
    ]

    deleted_count, _ = Review.objects.filter(
        review_type='external',
        external_author__in=authors,
    ).delete()

    print(f"Se eliminaron {deleted_count} reseñas externas")


class Migration(migrations.Migration):

    dependencies = [
        ('pieces', '0004_review_external_author_review_review_type_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_reviews, reverse_code=unseed_reviews),
    ]
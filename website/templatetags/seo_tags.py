import json
from urllib.parse import urljoin

from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.encoding import iri_to_uri

from website.seo import ARTICLE_TOPICS, CLINIC_ID, ORIGIN, PAGE_METADATA, SERVICE_ENTITIES

register = template.Library()


@register.simple_tag(takes_context=True)
def seo_metadata(context):
    request = context.get("request")
    match = getattr(request, "resolver_match", None)
    route = getattr(match, "url_name", None)
    post = context.get("post")
    if route not in PAGE_METADATA and not (route == "blog_detail" and post):
        return {}
    canonical = ORIGIN + iri_to_uri(request.path)
    if post:
        topic = ARTICLE_TOPICS.get(post.slug)
        title = (topic[0] if topic else post.title) + " | Naren Ultrasound"
        description = (
            "Read about " + topic[1] + ". From Naren Ultrasound, Visakhapatnam."
            if topic else post.meta_description or " ".join(strip_tags(post.content).split()[:24])
        )
    else:
        title, description = PAGE_METADATA[route]

    website_id = ORIGIN + "/#website"
    page = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical,
        "name": title, "description": description,
        "isPartOf": {"@id": website_id}, "inLanguage": "en",
    }
    if route == "about":
        page["@type"] = "AboutPage"
        page["about"] = {"@id": CLINIC_ID}
    elif route == "contact":
        page["@type"] = "ContactPage"
        page["about"] = {"@id": CLINIC_ID}
    elif route in ("blog_list", "gallery"):
        page["@type"] = "CollectionPage"
    graph = [
        {"@type": "WebSite", "@id": website_id, "url": ORIGIN + "/",
         "name": "Naren Ultrasound & Fetal Medicine Center",
         "publisher": {"@id": CLINIC_ID}, "inLanguage": "en"},
        page,
    ]
    if route == "services":
        page["mainEntity"] = []
        for fragment, name in SERVICE_ENTITIES:
            service_id = canonical + "#" + fragment
            page["mainEntity"].append({"@id": service_id})
            graph.append({
                "@type": "Service", "@id": service_id, "url": service_id,
                "name": name, "provider": {"@id": CLINIC_ID},
            })
    elif route == "doctors":
        # Name and profile URL come from the existing visible doctor profile.
        # Do not infer authorship, review, qualifications or affiliations.
        person_id = canonical + "#person"
        page["mainEntity"] = {"@id": person_id}
        graph.append({
            "@type": "Person", "@id": person_id,
            "name": "Dr. Naren Satya", "url": canonical,
            "mainEntityOfPage": {"@id": page["@id"]},
        })
    if post:
        article = {
            "@type": "BlogPosting", "@id": canonical + "#article",
            "url": canonical, "headline": post.title, "description": description,
            "mainEntityOfPage": {"@id": page["@id"]},
            "publisher": {"@id": CLINIC_ID}, "inLanguage": "en",
        }
        # Default model authors and administrative timestamps are not proof of
        # authorship, publication or medical review. Omit pending verification.
        if post.featured_image:
            article["image"] = urljoin(ORIGIN, post.featured_image.url)
        page["mainEntity"] = {"@id": article["@id"]}
        graph.append(article)
    serialized = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=True)
    serialized = serialized.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return {"title": title, "description": description, "schema": mark_safe(serialized)}

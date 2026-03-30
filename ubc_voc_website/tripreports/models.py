from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.safestring import mark_safe

from ubc_voc_website.utils import is_member

import json
from django_quill.widgets import QuillWidget
from modelcluster.fields import ParentalManyToManyField
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

class TripReport(Page):
    body = models.TextField(blank=True, null=True)
    trip = models.ForeignKey(
        "trips.Trip",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="trip_report"
    )

    categories = ParentalManyToManyField("tripreports.TripReportCategory", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body', widget=QuillWidget),
        FieldPanel('trip'),
        FieldPanel('categories'),
        FieldPanel('is_private'),
        FieldPanel("legacy_pdf")
    ]
    parent_page_types = ['tripreports.TripReportIndexPage']

    old_id = models.IntegerField(blank=True, null=True)
    is_private = models.BooleanField(default=False)
    legacy_pdf = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )
    legacy_html = models.TextField(blank=True, null=True)

    def get_body_html(self):
        try:
            data = json.loads(self.body)
            return mark_safe(data.get("html", ""))
        except (json.JSONDecodeError, TypeError, AttributeError):
            if self.body:
                return mark_safe(self.body)
        
        if self.legacy_html:
            return mark_safe(self.legacy_html)

    def serve(self, request):
        if getattr(self, "is_private", False):
            if not request.user.is_authenticated:
                return redirect("/account/login/?next={self.url}")
            elif not is_member(request.user):
                return render(request, "access_denied.html", status=403)

        from .forms import CommentForm
        if request.method == "POST":
            if is_member(request.user):
                form = CommentForm(request.POST)
                if form.is_valid():
                    comment = form.save(commit=False)
                    comment.trip_report = self
                    comment.user = request.user
                    comment.save()
                    return redirect(self.url)       
        else:
            form = CommentForm()

        context = super().get_context(request)
        context["form"] = form
        # only top-level comments; replies are accessible via `comment.replies`
        context["comments"] = self.comments.filter(parent__isnull=True).order_by("timestamp").prefetch_related("replies", "replies__user__profile")
        return TemplateResponse(request, self.get_template(request), context)

class Comment(models.Model):
    trip_report = models.ForeignKey(
        TripReport,
        on_delete=models.CASCADE,
        related_name="comments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    body = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )

class TripReportIndexPage(Page):
    intro = RichTextField(blank=True)
    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]
    subpage_types = ['tripreports.TripReport']

    def get_context(self, request):
        context = super().get_context(request)

        sort_order = request.GET.get("sort", "desc")
        order_by = "first_published_at" if sort_order == "asc" else "-first_published_at"

        reports = TripReport.objects.child_of(self).live().public().select_related(
            "owner__profile"
            ).prefetch_related(
                "categories"
            ).order_by(
                order_by
            )

        if not request.user.is_authenticated or not is_member(request.user):
            reports = reports.filter(is_private=False)

        q = request.GET.get("q")
        if q:
            reports = reports.filter(models.Q(title__icontains=q) | models.Q(body__icontains=q))

        category_id = request.GET.get("category")
        if category_id and category_id != "all":
            reports = reports.filter(categories__id=category_id)

        page = request.GET.get("page")
        paginator = Paginator(reports, 50)
        try:
            reports = paginator.page(page)
        except PageNotAnInteger:
            reports = paginator.page(1)
        except EmptyPage:
            reports = paginator.page(paginator.num_pages)

        context["reports"] = reports
        context["categories"] = TripReportCategory.objects.all()
        context["sort"] = sort_order
        return context
    
@register_snippet
class TripReportCategory(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Trip Report Categories"
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from .models import Poll, Choice, Vote


class IndexView(generic.ListView):
    template_name = "polls/index.html"
    context_object_name = "polls"
    paginate_by = 10

    def get_queryset(self):
        queryset = Poll.objects.filter(
            pub_date__lte=timezone.now(), choice__isnull=False
        ).distinct()

        # sort queryset by date (by default) or by name
        queryset = queryset.order_by("pub_date")
        sort = self.request.GET.get("sort")
        match sort:
            case "-date":
                queryset = queryset.order_by("-pub_date")
            case "name":
                queryset = queryset.order_by("text")
            case "-name":
                queryset = queryset.order_by("-text")
            case "votes":
                queryset = sorted(queryset, key=lambda x: x.total_votes, reverse=True)
            case "-votes":
                queryset = sorted(queryset, key=lambda x: x.total_votes)
        return queryset


class DetailView(generic.DetailView):
    model = Poll
    template_name = "polls/detail.html"
    context_object_name = "poll"
    queryset = Poll.objects.filter(
        pub_date__lte=timezone.now(), choice__isnull=False
    ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            return context

        poll = self.get_object()
        choices = poll.get_choices_with_params()
        context["choices"] = choices

        # if user already voted in the current pole
        # pass the user choice to the template so voted choices will be checked
        all_user_votes = Vote.objects.filter(user=self.request.user)
        if votes := all_user_votes.filter(poll=poll):
            user_choices = [vote.choice.pk for vote in votes]
            context["user_choices"] = user_choices
        return context


@login_required(redirect_field_name=None)
def vote(request, pk):
    redirect = HttpResponseRedirect(reverse("polls:detail", args=(pk,)))

    if request.method != "POST":
        return redirect

    user = request.user
    poll = get_object_or_404(Poll, pk=pk)
    choices = request.POST.getlist("choice")
    action = request.POST.get("action")

    # do not delete admin votes
    votes = Vote.objects.filter(user=user, poll=poll)
    if not user.is_superuser and votes:
        votes.delete()

    # create votes only if clicked 'Vote' button
    if action == "vote":
        for choice in choices or []:
            choice = Choice.objects.get(pk=choice)
            Vote.objects.create(user=user, poll=poll, choice=choice)
    return redirect

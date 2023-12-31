from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import View
from .models import Movie, Category, Actor, Genre, Rating
from .forms import ReviewForm, RatingForm


class GenreYear:

    def get_genres(self):
        return Genre.objects.all()

    def get_years(self):
        return Movie.objects.filter(draft=False).order_by("year").distinct().values('year')


class MovieView(GenreYear, ListView):
    model = Movie
    queryset = Movie.objects.filter(draft=False)

class MovieDetailView(GenreYear, DetailView):
    model = Movie
    slug_field = 'url'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["star_form"] = RatingForm
        return context


    def get_user_stars(self, ip, movie_id):
        if Rating.objects.filter(ip=ip, movie_id=movie_id).exists():
            stars = Rating.objects.get(ip=ip, movie_id=movie_id).star
        else:
            stars = None
        return stars

    def get(self, request, *args, **kwargs):
        ip = AddStarRating.get_client_ip(self, self.request)
        movie_id = Movie.objects.get(url=kwargs['slug']).id
        stars = self.get_user_stars(ip, movie_id)
        self.object = self.get_object()
        context = self.get_context_data(object=self.get_object)
        if stars:
            context['stars'] = str(stars)

        return self.render_to_response(context)


class AddReview(GenreYear, View):
    def post(self, request, pk):
        form = ReviewForm(request.POST)
        movie = Movie.objects.get(id=pk)
        if form.is_valid():
            form = form.save(commit=False)
            if request.POST.get('parent', None):
                form.parent_id = int(request.POST.get('parent'))
            form.movie = movie
            form.save()
        return redirect(movie.get_absolute_url())


class ActorView(GenreYear, DetailView):
    model = Actor
    template_name = "movies/actor.html"
    slug_field = "name"


class FilterMoviesView(GenreYear, ListView):
    def get_queryset(self):
        if self.request.GET.getlist("year") and self.request.GET.getlist("genre"):
            queryset = Movie.objects.filter(Q(year__in=self.request.GET.getlist("year")),
                                            Q(genres__in=self.request.GET.getlist("genre")))
        elif not self.request.GET.getlist("genre"):
            queryset = Movie.objects.filter(Q(year__in=self.request.GET.getlist("year")))
        elif not self.request.GET.getlist("year"):
            queryset = Movie.objects.filter(Q(genres__in=self.request.GET.getlist("genre")))
        return queryset


class AddStarRating(View):
    """Добавление рейтинга фильму"""
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request):
        form = RatingForm(request.POST)
        if form.is_valid():
            Rating.objects.update_or_create(
                ip=self.get_client_ip(request),
                movie_id=int(request.POST.get("movie")),
                defaults={'star_id': int(request.POST.get("star"))}
            )
            return HttpResponse(status=201)
        else:
            return HttpResponse(status=400)

class Search(ListView):
    def get_queryset(self):
        return Movie.objects.filter(title__icontains=self.request.GET.get("q"))

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["q"] = self.request.GET.get("q")
        return context
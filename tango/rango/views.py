from django.shortcuts import render, redirect
from rango.models import Category, Page
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from datetime import datetime
from rango.bing_search import run_query

#@login_required
#def user_logout(request):
#    logout(request)
#    return HttpResponseRedirect('/rango/')

@login_required
def auto_add_page(request):
    cat_id = None
    url = None
    title = None
    context_dict = {}
    if request.method == 'GET':
        cat_id = request.GET['category_id']
        url = request.GET['url']
        title = request.GET['title']
        if cat_id:
            category = Category.objects.get(id=int(cat_id))
            p = Page.objects.get_or_create(category=category, title=title, url=url)

            pages = Page.objects.filter(category=category).order_by('-views')

            # Adds our results list to the template context under name pages.
            context_dict['pages'] = pages

    return render(request, 'rango/page_list.html', context_dict)

def get_category_list(max_results=0, starts_with=''):
        cat_list = []
        if starts_with:
                cat_list = Category.objects.filter(name__istartswith=starts_with)

        if max_results > 0:
                if len(cat_list) > max_results:
                        cat_list = cat_list[:max_results]

        return cat_list

def suggest_category(request):

        cat_list = []
        starts_with = ''
        if request.method == 'GET':
                starts_with = request.GET['suggestion']

        cat_list = get_category_list(8, starts_with)

        return render(request, 'rango/category_list.html', {'cat_list': cat_list })
    
@login_required
def restricted(request):
    return HttpResponse("Since you're logged in, you can see this text!")

#def user_login(request):
#    if request.method == "POST":

#        username = request.POST.get('username')
#        password = request.POST.get('password')
#        user = authenticate(username=username, password=password)
#        if user:
#            if user.is_active:
#                login(request, user)
#                return HttpResponseRedirect('/rango/')
#            else:
#                return HttpResponse("Your Rango account is disabled.")
#        else:
#            print "Invalid login details: {0}, {1}".format(username, password)
#            return HttpResponse("Invalid login details supplied.")
#    else:
#        return render(request, 'rango/login.html', {})

##def register(request):
##
##       
##    registered = False
##
##    if request.method == 'POST':
##        user_form = UserForm(data=request.POST)
##        profile_form = UserProfileForm(data=request.POST)
##
##        if user_form.is_valid() and profile_form.is_valid():
##            user = user_form.save()
##            user.set_password(user.password)
##            user.save()
##            profile = profile_form.save(commit=False)
##            profile.user = user
##
##            if 'picture' in request.FILES:
##                profile.picture = request.FILES['picture']
##            profile.save()
##            registered = True
##
##        else:
##            print user_form.errors, profile_form.errors
##
##    else:
##        user_form = UserForm()
##        profile_form = UserProfileForm()
##
##    return render(request,
##            'rango/register.html',
##            {'user_form':user_form, 'profile_form':profile_form, 'registered':registered})


@login_required
def like_category(request):

    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']

    likes = 0
    if cat_id:
        cat = Category.objects.get(id=int(cat_id))
        if cat:
            likes = cat.likes + 1
            cat.likes =  likes
            cat.save()

    return HttpResponse(likes)

def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()

    return render(request, 'rango/add_category.html', {'form':form})

def add_page(request, category_name_slug):

    try:
        cat = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
            cat = None
            
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            if cat:
                page = form.save(commit=False)        
                page.category = cat
                page.views = 0
                page.save()
            return category(request, category_name_slug)
        else:
            print form.errors
    else:
        form = PageForm()

    context_dict = {'form':form, 'category':cat}

    return render(request, 'rango/add_page.html', context_dict)

def category(request, category_name_slug):
    context_dict = {}
    context_dict['result_list'] = None
    context_dict['query'] = None
    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

            context_dict['result_list'] = result_list
            context_dict['query'] = query

    try:
        category = Category.objects.get(slug=category_name_slug)
        context_dict['category_name'] = category.name
        pages = Page.objects.filter(category=category).order_by('-views')
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass

    if not context_dict['query']:
        context_dict['query'] = category.name

    return render(request, 'rango/category.html', context_dict)

def index(request):

    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    
    context_dict = {'categories': category_list, 'pages': page_list}

    # Get the number of visits to the site.
    # We use the COOKIES.get() function to obtain the visits cookie.
    # If the cookie exists, the value returned is casted to an integer.
    # If the cookie doesn't exist, we default to zero and cast that.
    visits = request.session.get('visits')
    if not visits:
        visits = 1

    reset_last_visit_time = False
    last_visit = request.session.get('last_visit')
    if last_visit:
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

        if (datetime.now() - last_visit_time).days > 0:
            visits = visits + 1
            # ...and flag that the cookie last visit needs to be updated
            reset_last_visit_time = True
    else:
        # Cookie last_visit doesn't exist, so flag that it should be set.
        reset_last_visit_time = True

    if reset_last_visit_time:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = visits
    context_dict['visits'] = visits

    response = render(request, 'rango/index.html', context_dict)
    return response
        
def about(request):

    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0
    context_dict = {'boldmessage': "I am bold font from the context", 'visits': count}
    return render(request, 'rango/about.html', context_dict)

def search(request):

    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render(request, 'rango/search.html', {'result_list': result_list})

def track_url(request):
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

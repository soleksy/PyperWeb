from flask import Flask , render_template ,redirect,url_for,request ,session
from flaskapp import app, db
from flaskapp.forms import InfoForm
from flaskapp.models import Article
from .APIS.ARXIV.ArxivClasses import ArxivHelper,ArxivParser
from .APIS.HEP.HepClasses import HepHelper ,  HepParser
import asyncio , httpx
from .constants import SIZE , ITEMS_PER_PAGE 
from sqlalchemy import create_engine
import sqlalchemy


articles = [] # stores list entities
filteredArticleList = [] # stores articles post filters
visibleArticles = [] # stores articles that are being displayed atm

searchController = 0 # controlls whether the initial search was processed
searched = False #?
page = 0 # basic controlling attribute
startDate = None # controlls the filters
endDate = None # controlls the filters

def updateArticleList(listOfArticles):    
    global articles
    articles = listOfArticles

def sortByDateAscending(list):
    return sorted(list,key=lambda x:x['Year'] , reverse=False)

def sortByDateDescending(list):
    return sorted(list,key=lambda x:x['Year'] , reverse=True)

def filterArticles(list):
    articleFilter = dict()
    newArticleList = []
    
    for article in list:
        if article.get('Doi'):
            if articleFilter.get(article['Doi']):
                continue
            else:
                articleFilter[article['Doi']] = True
                newArticleList.append(article)
        elif article.get('eprint'):
            if articleFilter.get(article['eprint']):
                continue       
            else:
                articleFilter[article['eprint']] = True
                newArticleList.append(article)
        else:
            if article.get('Title'):
                if article.get('Year'):
                    if articleFilter.get(article['Title']):
                        if articleFilter.get(article['Year']):
                            if articleFilter.get(article['Title']).get('Year') == article['Year']:
                                continue
                            else:
                                articleFilter[article['Title']] = {'Year':article['Year']}
                                newArticleList.append(article)
                        else:
                            articleFilter[article['Title']] = {'Year':article['Year']}
                            newArticleList.append(article)
                    else:
                        articleFilter[article['Title']] = {'Year':article['Year']}
                        newArticleList.append(article)
                else:
                    articleFilter[article['Title']] = {'Year':None}
                    newArticleList.append(article)
            else:
                continue
    return newArticleList
                        
async def retrieveData(url : str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url,timeout=100)
        await client.aclose()
    return resp

def clearData(session):
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()

def checkTableExistance(tableName):
    engine = create_engine("sqlite:////tmp/test.db")
    if sqlalchemy.inspect(engine).has_table(tableName):
        return True
    else:
        return False
    

@app.route('/' , methods=['GET' ,'POST'])
def indexPage():
    global searchController
    if request.method == "POST":
        searchController = 1
        text = request.form["searchText"]
        if text == "":
            text = " "
            
        ARXIV = request.form.get('arxiv')
        if ARXIV == None:
            ARXIV = False
        else:
            ARXIV = True

        HEP = request.form.get('hep')
        if HEP == None:
            HEP = False
        else:
            HEP = True
        
        return redirect(url_for('searchResults',txt=text,hep=HEP,arxiv=ARXIV,filters=0,page=1))
    else:
        return render_template('index.html')
    

@app.route('/search_results/<txt>/hep<hep>/arx<arxiv>/filters<filters>' , methods=['GET' ,'POST'])
async def searchResults(txt,hep,arxiv,filters):

    global searchController
    global startDate
    global endDate
    
    global articles #original search
    global filteredArticleList #post filter
    global visibleArticles #articles being displayed
    global searched

    
    arxivArticleList = []
    hepArticleList = []
    
    dbToSearch = []
    listOfApiCalls = []
    index = 0
    LocalArticles = []
    
    #handle date range submit
    form = InfoForm()
    if form.validate_on_submit():
        tempStartDate = startDate
        tempEndDate = endDate
        startDate = form.startDate.data.strftime("%m/%d/%Y")
        endDate = form.endDate.data.strftime("%m/%d/%Y")
        startYear = int(form.startDate.data.strftime("%Y"))
        endYear = int(form.endDate.data.strftime("%Y"))
        
        LocalArticles = Article.query.filter(Article.yearPublished<=endYear,Article.yearPublished>=startYear).paginate(page=1,per_page=ITEMS_PER_PAGE)
        
        if len(LocalArticles) == 0:
            startDate = tempStartDate
            endDate = tempEndDate
            return render_template('search_results.html' , hep=hep,txt=txt,arxiv=arxiv, results=LocalArticles , form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        else:
            searched = True
            return render_template('search_results.html' , hep=hep,arxiv=arxiv,results=LocalArticles,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
    
    if request.method == "POST":
        articleID = request.form.get("info")
        return redirect(url_for('articlePage',id = articleID))

    elif searchController == 1:
        searched = False
        startDate = None
        endDate = None
        
        if arxiv:
            arxivHelper = ArxivHelper()
            url = arxivHelper.allParamSearch(txt)
            listOfApiCalls.append(retrieveData(url))
                
        if hep :
            hepHelper = HepHelper()
            url = hepHelper.hepUrlGenerator(txt)
            listOfApiCalls.append(retrieveData(url))

        async with httpx.AsyncClient() as client:
            dbToSearch = await asyncio.gather(
                *listOfApiCalls
            )
            await client.aclose()

        if arxiv:
            arxivParser = ArxivParser(dbToSearch[index].content)
            arxivParser.standardizeXml()
            arxivParser.parseXML()
            arxivArticleList = arxivParser.ListOfArticles
            index += 1
        if hep:
            hepParser = HepParser(dbToSearch[index].content)
            hepParser.parseJsonFile()
            hepArticleList = hepParser.ListOfArticles
            index += 1

        searchController = 0
    
        updateArticleList(sortByDateDescending(filterArticles(hepArticleList + arxivArticleList)))
        
        if len(articles) == 0:
            session['searchURL'] = None
        else:
            if checkTableExistance("Article"):
                clearData(db.session)
            else:
                db.create_all()
            
            for article in articles:
                db.session.add(Article(title=article.get('Title'), description=article.get('Summary'), source=article.get('DB')
                                       ,firstAuthor=article.get('FirstAuthor'), yearPublished=article.get('Year'),
                                       numberOfAuthors=article.get('AuthorCount'),journal=article.get('Journal'),
                                       volume=article.get('Volume'),pages=article.get('Pages'),DOI=article.get('Doi'),
                                       eprint=article.get('eprint'),bibtex=article.get('Bibtex')))
            db.session.commit()
            session['searchURL'] = f"/search_results/{txt}/hep{hep}/arx{arxiv}/filters{filters}"
            
            page = request.args.get('page',1,type=int)
            articles= Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
        return render_template('search_results.html' ,page=page,hep=hep,arxiv=arxiv, results=articles  ,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        
    else:
        if(searchController == 0):
            page = request.args.get('page',1,type=int)
            articles= Article.query.paginate(page=page,per_page=ITEMS_PER_PAGE)
            return render_template('search_results.html' ,hep=hep,arxiv=arxiv, results=articles  ,txt=txt, form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
            
        if filters == "1":

            searchController = 0
            searched = False

            startDate = None
            endDate = None
            
            return render_template('search_results.html' , hep=hep,arxiv=arxiv, results=articles, txt=txt ,form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        if len(filteredArticleList) == 0 and not searched:
            startDate = None
            endDate = None
            return render_template('search_results.html' ,hep=hep,arxiv=arxiv,  results=articles, txt=txt ,form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        elif len(filteredArticleList) == 0 and searched:
            return render_template('search_results.html' , hep=hep,arxiv=arxiv, results=articles, txt=txt,form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))
        else:
            return render_template('search_results.html' , hep=hep,arxiv=arxiv,results=articles, txt=txt,form=form,startDate=startDate,endDate=endDate,searchURL=session.get('searchURL'))

@app.route('/search_results/<id>')
def articlePage(id):
    global articles
    global filteredArticleList
    global searched
    if searched:
        if len(articles) == 0:
            article = articles.items[int(id)]
            bibtex = articles.items[int(id)].bibtex
        else:
            article = articles.items[int(id)]
            bibtex = articles.items[int(id)].bibtex
    else:
        article = articles.items[int(id)]
        bibtex = articles.items[int(id)].bibtex

    return render_template('article.html' , bibtex=bibtex, article=article ,searchURL=session.get('searchURL'),)


@app.route('/about')
def about():
    return render_template('about.html')

################################################################################################################################################################

#GJ DE SWARDT
#COURSE2VEC

################################################################################################################################################################
#1.) SETUP

##Import libraries
import psycopg2
import configparser
import pathlib
import pandas
import numpy
import warnings
import timeit
import gensim.models
import plotly.express
from sklearn.manifold import TSNE

##Connect config file
config = configparser.ConfigParser()
config_file = str(pathlib.Path.home())+'/config.ini'
config.read(config_file)

################################################################################################################################################################
#2.) EXTRACT DATA

##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Course Table
##Sql query
sql = """
SELECT DISTINCT B.course_code,
                CONCAT(A.university_code, '-', A.course_abbreviation) AS course_abbreviation,
                A.course_name AS course,
                A.university_code AS university_abbreviation,
                A.university
FROM rdw_bcd.vw_bcd_opportunity A
LEFT JOIN rdw_bcd.vw_bcd_presentation B ON B.presentation_code = A.presentation_code
"""

##Create pandas dataframe
df_course = pandas.read_sql_query(sql, rdw_conn)

##Edit course table
##Remove NaN's
df_course = df_course.dropna()

##Transform floats to integers
df_course['course_code'] = 'A' + df_course['course_code'].astype(str)

##View data
print(df_course)

##Opportunity Table
##Sql query
sql = """
SELECT person_code,
       B.course_code
FROM rdw_bcd.vw_bcd_opportunity A
LEFT JOIN rdw_bcd.vw_bcd_presentation B ON B.presentation_code = A.presentation_code
"""

##Create pandas dataframe
df_opportunity = pandas.read_sql_query(sql, rdw_conn)

##Edit opportunity table
##Remove NaN's
df_opportunity = df_opportunity.dropna()

##Transform floats to integers
df_opportunity['person_code'] = 'A' + df_opportunity['person_code'].astype(str)
df_opportunity['course_code'] = 'A' + df_opportunity['course_code'].astype(str)

##View data
print(df_opportunity)

################################################################################################################################################################
#3.) MODELLING

##Model Input
##Create a list
course_list = df_opportunity.sort_values(['person_code', 'course_code'])[['person_code', 'course_code']].values.tolist()

##Create product corpus
course_corpus = []
sentence = []
new_person_code = course_list[0][0]
for (person_code, course_code) in course_list:
    if new_person_code != person_code:
        course_corpus.append(sentence)
        sentence = []
        new_person_code = person_code
    sentence.append(str(course_code))

##Train word2vec model
start = timeit.default_timer()
model = gensim.models.Word2Vec(course_corpus, window=2, size=100, workers=4, min_count=10, sg=1)
stop = timeit.default_timer()
print('Time: ', stop - start)

##Function to return product description rather than product code
def toCourseName(id):
    return df_course[df_course['course_code'] == id]['course_abbreviation'].values.tolist()[0]

##Function to create similarity list using cosine similarity
def most_similar_readable(model, course_code):
    similar_list = [(course_code, 1.0)] + model.wv.most_similar(course_code)
    return [(toCourseName((id)), similarity ) for (id, similarity) in similar_list]

#df_course[df_course['course_code'] == id]['course_abbreviation'].values.tolist()[0]

pandas.DataFrame(most_similar_readable(model, 'A1.0'), columns=['course', 'similarity'])

##T-SNE dimension reduction
labels = []
tokens = []

for word in model.wv.vocab:
    tokens.append(model[word])
    labels.append(df_course['course_abbreviation'][df_course['course_code'] == word].to_string(index=False))

tsne_model = TSNE(perplexity=40, n_components=2, init='pca', n_iter=500, random_state=23)
new_values = tsne_model.fit_transform(tokens)

##Add x and y co-ordinates to dataframe
#df_tsne_coordinates['course_abbreviation'] = pandas.DataFrame({'course_abbreviation':labels, 'x':new_values[:,0], 'y':new_values[:,1]})
#df_tsne_coordinates

##Add x and y co-ordinates to dataframe
df_tsne_coordinates = pandas.DataFrame({'course_abbreviation':labels, 'x':new_values[:,0], 'y':new_values[:,1]})
df_tsne_coordinates['course_abbreviation'] = df_tsne_coordinates['course_abbreviation'].str.strip()
df_course_tsne = pandas.merge(left=df_course, right=df_tsne_coordinates, how='inner', on='course_abbreviation')
df_course_tsne.head(10)

plotly.express.scatter(data_frame=df_course_tsne,
                       x=df_course_tsne['x'],
                       y=df_course_tsne['y'],
                       hover_name=df_course_tsne['course'],
                       color=df_course_tsne['university'],
                       #text=df_course_tsne['course_abbreviation'],
                       width=1000,
                       height=1000).show()


df_course_tsne[df_course_tsne['course_abbreviation'] == 'CAM-BSM']
pandas.DataFrame(most_similar_readable(model, 'A233.0'), columns=['course', 'similarity'])

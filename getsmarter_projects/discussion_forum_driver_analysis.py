################################################################################################################################################################

# GJ DE SWARDT
# DISCUSSION FORUM DRIVER ANALYSIS

################################################################################################################################################################
#1.) SETUP

##Import libraries
import pandas
import numpy
import psycopg2
import configparser
import pathlib
import plotly.express

##Connect config file
config = configparser.ConfigParser()
config_file = str(pathlib.Path.home())+'/Documents/projects/useful_stuff/config.ini'
config.read(config_file)

################################################################################################################################################################
#2.) EXTRACT DATA FOR CORRELATION ANALYSIS

##2.1) Extract data from database
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT B.university,
       B.university_code AS university_abbreviation,
       B.course_name AS course,
       CONCAT(B.university_code, '-', B.course_abbreviation) AS course_abbreviation,
       B.presentation_name AS presentation,
       B.presentation_abbreviation,
       A.vle_course_id,
       B.presentation_start_date,
       E.activity_type,
       E.activity_name,
       B.course_type,
       B.subject_vertical,
       B.customer_tribe,
       A.vle_user_id,
       E.student_name,
       A.final_mark,
       E.number_of_posts
FROM rdw_bcd.vw_bcd_enrolment A
LEFT JOIN rdw_bcd.vw_bcd_registration B ON B.registration_id = A.registration_id
LEFT JOIN rdw_bcd.vw_bcd_presentation C ON C.presentation_code = A.presentation_code
LEFT JOIN rdw_bcd.vw_bcd_partner D ON D.vle_credential_id = C.vle_credential_id
                                   AND D.university_code = C.university_code
LEFT JOIN (SELECT university AS la_university,
                  course_id AS vle_course_id,
                  user_id AS vle_user_id,
                  activity_type,
                  activity_name,
                  user_role,
                  CONCAT(firstname, ' ', lastname) AS student_name,
                  SUM(all_posts) AS number_of_posts
           FROM rdw_la.vw_master_alluser_activities
           WHERE user_role = 'student'
           AND (LOWER(activity_name) LIKE '%class-wide%'
                OR LOWER(activity_name) LIKE '%class wide%')
           AND LOWER(module_name) NOT LIKE '%orientation%'
           GROUP BY university,
                    course_id,
                    activity_type,
                    activity_name,
                    user_id,
                    user_role,
                    CONCAT(firstname, ' ', lastname)) E ON E.la_university = D.la_university
                                                        AND E.vle_course_id = A.vle_course_id
                                                        AND E.vle_user_id = A.vle_user_id
WHERE C.product_life_cycle_status = 'Completed'
AND A.status IN ('Pass', 'Fail')
AND A.vle_user_id IS NOT NULL
AND A.vle_course_id IS NOT NULL;
"""

##Create pandas dataframe
df_extract = pandas.read_sql_query(sql, rdw_conn)

##2.2) Clean data
##Clean df_extract
df_extract = df_extract.fillna(0)
df_extract['final_mark'].values[df_extract['final_mark'].values > 100] = 100
print(df_extract.head(20))
print('Number of Total Students:', len(df_extract))

##2.3) Create subset dataframes
##Create dataframe for number of post greater than 1
df_greater_than_1 = df_extract[df_extract['number_of_posts'] > 1]
print(df_greater_than_1.head(20))
print('Number of Total Students (Posts greater than 1):', len(df_greater_than_1))

##Create dataframe for number of post less than 10
df_greater_than_5 = df_extract[df_extract['number_of_posts'] > 5]
print(df_greater_than_5.head(20))
print('Number of Total Students (Posts greater than 5):', len(df_greater_than_5))

##Create dataframe for number of post less than 10
df_greater_than_10 = df_extract[df_extract['number_of_posts'] > 10]
print(df_greater_than_10.head(20))
print('Number of Total Students (Posts greater than 10):', len(df_greater_than_10))

##Create subset for dreamers and realists
subset_values = ['Dreamers', 'Realists']
df_dreamers_realists = df_extract[df_extract['customer_tribe'].isin(subset_values)]
print(df_dreamers_realists.head(20))
print('Number of Dreamers and Realists:', len(df_dreamers_realists))

################################################################################################################################################################
#3.) CORRELATION CALCULATIONS (TOTAL LEVEL)

##3.1) Example of what correlation should look like

##Create data that is normally distributed with strong positive relatonship
##Set parameters
x = numpy.array([0, 100])
y = numpy.array([0, 100])
means = [x.mean(), y.mean()]
stds = [x.std() / 3, y.std() / 3]
corr = 0.8
covs = [[stds[0]**2, stds[0]*stds[1]*corr],
        [stds[0]*stds[1]*corr, stds[1]**2]]

##Generate data and put into dataframe
df_testdata = pandas.DataFrame(numpy.random.multivariate_normal(means, covs, 1000), columns=['final_mark', 'number_of_posts'])

##View dataframe
print(df_testdata)

##Create figure object
fig_corr_example = plotly.express.scatter(data_frame=df_testdata,
                                          x=df_testdata['final_mark'],
                                          y=df_testdata['number_of_posts'],
                                          title='Perfect Scenario: Number of Posts by Final Grade',
                                          trendline='ols',
                                          trendline_color_override='red',
                                          labels={'number_of_posts': 'Number of Posts',
                                                  'final_mark': 'Final Mark'})

##Save figure
fig_corr_example.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_corr_example.png')

##3.2) Analysis over all courses
##Calculate the correlation over all the courses
total_corr = df_extract['final_mark'].corr(df_extract['number_of_posts'])
print('R-squared on a total level:', total_corr**2)

##Plot posts by final mark
fig_corr_total = plotly.express.scatter(data_frame=df_extract,
                                        x=df_extract['final_mark'],
                                        y=df_extract['number_of_posts'],
                                        title='Number of Posts by Final Grade',
                                        trendline='ols',
                                        trendline_color_override='red',
                                        hover_data=['number_of_posts',
                                                    'final_mark',
                                                    'course_abbreviation'],
                                        labels={'number_of_posts': 'Number of Posts',
                                                'final_mark': 'Final Mark',
                                                'course_abbreviation': 'Course Abbreviation'})

##Edit axes
fig_corr_total.update_yaxes(range=[0, 100])
fig_corr_total.update_xaxes(range=[0, 100])

##Edit mark size
fig_corr_total.update_traces(marker=dict(size=5))
fig_corr_total.show()

##Save figure
fig_corr_total.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_corr_total.png')

##3.3) Analysis for greater than 1
##Calculate the correlation over all the courses
greater_than_1_corr = df_greater_than_1['final_mark'].corr(df_greater_than_1['number_of_posts'])
print('R-squared where posts more than 1:', greater_than_1_corr**2)

##3.4) Analysis for greater than 5
##Calculate the correlation over all the courses
greater_than_5_corr = df_greater_than_5['final_mark'].corr(df_greater_than_5['number_of_posts'])
print('R-squared where posts more than 5:', greater_than_5_corr**2)

##3.5) Analysis for greater than 10
##Calculate the correlation over all the courses
greater_than_10_corr = df_greater_than_10['final_mark'].corr(df_greater_than_10['number_of_posts'])
print('R-squared where posts more than 10:', greater_than_10_corr**2)

#3.6) Calculate correlation over all the courses only using Passive's and Dreamers
##Calculate correlation over all courses for dreamers and realists
dreamers_realists_corr = df_dreamers_realists['final_mark'].corr(df_dreamers_realists['number_of_posts'])
print('R-squared for dreamers realists:', dreamers_realists_corr**2)

##Create figure object
fig_dreamers_realists = plotly.express.scatter(data_frame=df_dreamers_realists,
                                               x=df_dreamers_realists['final_mark'],
                                               y=df_dreamers_realists['number_of_posts'],
                                               title='Dreamers and Realists: Number of Posts by Final Grade',
                                               trendline='ols',
                                               trendline_color_override='red',
                                               hover_data=['number_of_posts',
                                                           'final_mark',
                                                           'course_abbreviation'],
                                               labels={'number_of_posts': 'Number of Posts',
                                                       'final_mark': 'Final Mark',
                                                       'course_abbreviation': 'Course Abbreviation'})

##Edit axes
fig_dreamers_realists.update_yaxes(range=[0, 100])
fig_dreamers_realists.update_xaxes(range=[0, 100])

##Edit mark size
fig_dreamers_realists.update_traces(marker=dict(size=5))

##Save figure
fig_dreamers_realists.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_dreamers_realists.png')

################################################################################################################################################################
#4.) CORRELATION CALCULATIONS (COURSE LEVEL)

##Calculate correlation for each course abbreviation
df_corr_courses = pandas.DataFrame(df_extract.groupby('course_abbreviation')[['final_mark', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_courses = df_corr_courses[['course_abbreviation', 'number_of_posts']]
df_corr_courses = df_corr_courses.rename(columns={'number_of_posts': 'r_squared'})
df_corr_courses['r_squared'] = df_corr_courses['r_squared'] ** 2
df_corr_courses = df_corr_courses.sort_values(by='r_squared', ascending=False)

##View dataframe
print(df_corr_courses.head(20))

##Plot: GWU-SCO
##Create subset dataframe
df_gwu_sco = df_extract[df_extract['course_abbreviation'].str.contains('GWU-SCO')]

##View dataframe
print(df_gwu_sco.head(20))

##Create figure object
fig_gwu_sco = plotly.express.scatter(data_frame=df_gwu_sco,
                                     x=df_gwu_sco['final_mark'],
                                     y=df_gwu_sco['number_of_posts'],
                                     title='GWU-SCO: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['number_of_posts',
                                                 'final_mark',
                                                 'student_name'],
                                     labels={'number_of_posts': 'Number of Posts',
                                             'final_mark': 'Final Mark',
                                             'student_name': 'Student Name'})

##Save figure
fig_gwu_sco.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_gwu_sco.png')

##Plot: LSE-TFT
##Create subset dataframe
df_lse_tft = df_extract[df_extract['course_abbreviation'].str.contains('LSE-TFT')]

##View dataframe
print(df_lse_tft.head(20))

##Create figure object
fig_lse_tft = plotly.express.scatter(data_frame=df_lse_tft,
                                     x=df_lse_tft['final_mark'],
                                     y=df_lse_tft['number_of_posts'],
                                     title='LSE-TFT: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['number_of_posts',
                                                 'final_mark',
                                                 'student_name'],
                                     labels={'number_of_posts': 'Number of Posts',
                                             'final_mark': 'Final Mark',
                                             'student_name': 'Student Name'})

##Save figure
fig_lse_tft.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_lse_tft.png')

##Plot: SYR-FNM
##Create subset dataframe
df_syr_fnm = df_extract[df_extract['course_abbreviation'].str.contains('SYR-FNM')]

##View dataframe
print(df_syr_fnm.head(20))

##Create figure object
fig_syr_fnm = plotly.express.scatter(data_frame=df_syr_fnm,
                                     x=df_syr_fnm['final_mark'],
                                     y=df_syr_fnm['number_of_posts'],
                                     title='SYR-FNM: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['number_of_posts',
                                                 'final_mark',
                                                 'student_name'],
                                     labels={'number_of_posts': 'Number of Posts',
                                             'final_mark': 'Final Mark',
                                             'student_name': 'Student Name'})

##Save figure
fig_syr_fnm.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_syr_fnm.png')

##Plot: RICE-BDO
##Create subset dataframe
df_rice_bdo = df_extract[df_extract['course_abbreviation'].str.contains('RICE-BDO')]

##View dataframe
print(df_rice_bdo.head(20))

##Create figure object
fig_rice_bdo = plotly.express.scatter(data_frame=df_rice_bdo,
                                      x=df_rice_bdo['final_mark'],
                                      y=df_rice_bdo['number_of_posts'],
                                      title='RICE-BDO: Number of Posts by Final Grade',
                                      trendline='ols',
                                      trendline_color_override='red',
                                      hover_data=['number_of_posts',
                                                  'final_mark',
                                                  'student_name'],
                                      labels={'number_of_posts': 'Number of Posts',
                                              'final_mark': 'Final Mark',
                                              'student_name': 'Student Name'})

##Save figure
fig_rice_bdo.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_rice_bdo.png')

##Plot: RICE-RED
##Create subset dataframe
df_rice_red = df_extract[df_extract['course_abbreviation'].str.contains('RICE-RED')]

##View dataframe
print(df_rice_red.head(20))

##Create figure object
fig_rice_red = plotly.express.scatter(data_frame=df_rice_red,
                                      x=df_rice_red['final_mark'],
                                      y=df_rice_red['number_of_posts'],
                                      title='RICE-RED: Number of Posts by Final Grade',
                                      trendline='ols',
                                      trendline_color_override='red',
                                      hover_data=['number_of_posts',
                                                  'final_mark',
                                                  'student_name'],
                                      labels={'number_of_posts': 'Number of Posts',
                                              'final_mark': 'Final Mark',
                                              'student_name': 'Student Name'})

##Save figure
fig_rice_red.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_rice_red.png')

##Plot: UCT-MRS
##Create subset dataframe
df_uct_mrs = df_extract[df_extract['course_abbreviation'].str.contains('UCT-MRS')]

##View dataframe
print(df_uct_mrs.head(20))

##Create figure object
fig_uct_mrs = plotly.express.scatter(data_frame=df_uct_mrs,
                                     x=df_uct_mrs['final_mark'],
                                     y=df_uct_mrs['number_of_posts'],
                                     title='UCT-MRS: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['number_of_posts',
                                                 'final_mark',
                                                 'student_name'],
                                     labels={'number_of_posts': 'Number of Posts',
                                             'final_mark': 'Final Mark',
                                             'student_name': 'Student Name'})

##Save figure
fig_uct_mrs.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_uct_mrs.png')

################################################################################################################################################################
#5.) CORRELATION CALCULATIONS (SUBJECT VERTICAL GROUPS)

##Calculate correlation for each course abbreviation
df_corr_sub_vertical = pandas.DataFrame(df_extract.groupby('subject_vertical')[['final_mark', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_sub_vertical = df_corr_sub_vertical[['subject_vertical', 'number_of_posts']]
df_corr_sub_vertical = df_corr_sub_vertical.rename(columns={'number_of_posts': 'r_squared'})
df_corr_sub_vertical['r_squared'] = df_corr_sub_vertical['r_squared'] ** 2
df_corr_sub_vertical = df_corr_sub_vertical.sort_values(by='r_squared', ascending=False)
print(df_corr_sub_vertical.head(20))

##Plot: Politics subject vertical
##Create subset dataframe
df_politics = df_extract[df_extract['subject_vertical'].notnull()]
df_politics = df_politics[df_politics['subject_vertical'].str.contains('Politics')]
print(df_politics.head(20))
print('Number of Total Students in Politics vertical:', len(df_politics))

##Create figure object
fig_politics = plotly.express.scatter(data_frame=df_politics,
                                     x=df_politics['final_mark'],
                                     y=df_politics['number_of_posts'],
                                     title='Politics, Economics and International Relations: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['number_of_posts',
                                                 'final_mark'],
                                     labels={'number_of_posts': 'Number of Posts',
                                             'final_mark': 'Final Mark'})
import plotly.graph_objects
##Save figure
fig_politics.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_politics.png')

##Plot: Finance subject vertical
##Create subset dataframe
df_finance = df_extract[df_extract['subject_vertical'].notnull()]
df_finance = df_finance[df_finance['subject_vertical'].str.contains('Finance')]
print(df_finance.head(20))
print('Number of Total Students in Finance vertical:', len(df_finance))

##Create figure object
fig_finance = plotly.express.scatter(data_frame=df_finance,
                                     x=df_finance['final_mark'],
                                     y=df_finance['number_of_posts'],
                                     title='Finance: Number of Posts by Final Grade',
                                     trendline='ols',
                                     trendline_color_override='red')

fig_finance.show()

##Save figure
fig_finance.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_finance.png')

################################################################################################################################################################
#6.) CORRELATION CALCULATIONS (COURSE TYPE GROUPS)

##Calculate correlation for each course abbreviation
df_corr_course_type = pandas.DataFrame(df_extract.groupby('course_type')[['final_mark', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_course_type = df_corr_course_type[['course_type', 'number_of_posts']]
df_corr_course_type = df_corr_course_type.rename(columns={'number_of_posts': 'r_squared'})
df_corr_course_type['r_squared'] = df_corr_course_type['r_squared'] ** 2
df_corr_course_type = df_corr_course_type.sort_values(by='r_squared', ascending=False)
print(df_corr_course_type.head(20))

##Plot: Politics subject vertical
##Create subset dataframe
df_politics = df_extract[df_extract['subject_vertical'].notnull()]
df_politics = df_politics[df_politics['subject_vertical'].str.contains('Politics')]
print(df_politics.head(20))
print('Number of Total Students in Politics vertical:', len(df_politics))

################################################################################################################################################################
#5.) DRIVER ANALYSIS
##5.1) Extract data from database

##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT CONCAT(B.university_code, '-', B.course_abbreviation) AS course_abbreviation,
       B.course_type,
       B.subject_vertical,
       E.stakeholder_posts,
       E.stakeholder_likes,
       F.student_posts,
       F.student_likes,
       E.number_of_stakeholders,
       MAX(C.presentation_nr) AS number_of_presentations,
       COUNT(DISTINCT A.vle_user_id) AS number_of_students,
       SUM(CASE WHEN B.customer_tribe = 'Aspirants' THEN 1 ELSE 0 END) AS number_of_aspirants,
       SUM(CASE WHEN B.customer_tribe = 'Dreamers' THEN 1 ELSE 0 END) AS number_of_dreamers,
       SUM(CASE WHEN B.customer_tribe = 'Leaders' THEN 1 ELSE 0 END) AS number_of_leaders,
       SUM(CASE WHEN B.customer_tribe = 'Pros' THEN 1 ELSE 0 END) AS number_of_pros,
       SUM(CASE WHEN B.customer_tribe = 'Realists' THEN 1 ELSE 0 END) AS number_of_realists,
       SUM(CASE WHEN B.customer_tribe = 'Reinventors' THEN 1 ELSE 0 END) AS number_of_reinventors,
       ROUND(AVG(B.base_price), 2) AS average_course_price,
       ROUND(AVG(A.final_mark), 2) AS average_course_grade
FROM rdw_bcd.vw_bcd_enrolment A
LEFT JOIN rdw_bcd.vw_bcd_registration B ON B.registration_id = A.registration_id
LEFT JOIN rdw_bcd.vw_bcd_presentation C ON C.presentation_code = A.presentation_code
LEFT JOIN rdw_bcd.vw_bcd_partner D ON D.vle_credential_id = C.vle_credential_id
                                   AND D.university_code = C.university_code
LEFT JOIN (SELECT university AS la_university,
                  CONCAT(SPLIT_PART(course_name, '-', 1), '-', SPLIT_PART(course_name, '-', 2)) AS course_abbreviation,
                  COUNT(DISTINCT user_id) AS number_of_stakeholders,
                  SUM(all_posts) AS stakeholder_posts,
                  SUM(nr_of_likes) AS stakeholder_likes
           FROM rdw_la.vw_master_alluser_activities
           WHERE activity_type IN ('hsuforum', 'forum')
           AND user_role IN ('tutor', 'headtutor')
           AND (LOWER(activity_name) LIKE '%discussion forum%' OR LOWER(activity_name) LIKE '%class-wide%')
           AND LOWER(activity_name) NOT LIKE '%small-group%'
           AND LOWER(activity_name) NOT LIKE '%small group%'
           AND LOWER(activity_name) NOT LIKE '%graded%'
           AND LOWER(activity_name) NOT LIKE '%practical exercise%'
           AND LOWER(activity_name) NOT LIKE '%final assignment%'
           GROUP BY university,
                    CONCAT(SPLIT_PART(course_name, '-', 1), '-', SPLIT_PART(course_name, '-', 2))) E ON E.la_university = D.la_university
                                                                              AND E.course_abbreviation = CONCAT(B.university_code, '-', B.course_abbreviation)
LEFT JOIN (SELECT university AS la_university,
                  CONCAT(SPLIT_PART(course_name, '-', 1), '-', SPLIT_PART(course_name, '-', 2)) AS course_abbreviation,
                  SUM(all_posts) AS student_posts,
                  SUM(nr_of_likes) AS student_likes
           FROM rdw_la.vw_master_alluser_activities
           WHERE activity_type IN ('hsuforum', 'forum')
           AND user_role IN ('student')
           AND (LOWER(activity_name) LIKE '%discussion forum%' OR LOWER(activity_name) LIKE '%class-wide%')
           AND LOWER(activity_name) NOT LIKE '%small-group%'
           AND LOWER(activity_name) NOT LIKE '%small group%'
           AND LOWER(activity_name) NOT LIKE '%graded%'
           AND LOWER(activity_name) NOT LIKE '%practical exercise%'
           AND LOWER(activity_name) NOT LIKE '%final assignment%'
           GROUP BY university,
                    CONCAT(SPLIT_PART(course_name, '-', 1), '-', SPLIT_PART(course_name, '-', 2))) F ON F.la_university = D.la_university
                                                                              AND F.course_abbreviation = CONCAT(B.university_code, '-', B.course_abbreviation)
WHERE C.product_life_cycle_status = 'Completed'
AND A.status IN ('Pass', 'Fail')
AND A.vle_user_id IS NOT NULL
AND A.vle_course_id IS NOT NULL
GROUP BY CONCAT(B.university_code, '-', B.course_abbreviation),
         B.course_type,
         B.subject_vertical,
         E.stakeholder_posts,
         E.stakeholder_likes,
         F.student_posts,
         F.student_likes,
         E.number_of_stakeholders
"""

##Create pandas dataframe
df_driver_extract = pandas.read_sql_query(sql, rdw_conn)

##5.2) Clean data

##Drop columns with nulls
df_driver_extract = df_driver_extract.dropna(axis=0, how='any')
print(df_driver_extract)

##Clean data
##Divide customer tribe by number of students
df_driver_extract['proportion_aspirants'] = df_driver_extract['number_of_aspirants'] / df_driver_extract['number_of_students'] * 100
df_driver_extract['proportion_dreamers'] = df_driver_extract['number_of_dreamers'] / df_driver_extract['number_of_students'] * 100
df_driver_extract['proportion_leaders'] = df_driver_extract['number_of_leaders'] / df_driver_extract['number_of_students'] * 100
df_driver_extract['proportion_pros'] = df_driver_extract['number_of_pros'] / df_driver_extract['number_of_students'] * 100
df_driver_extract['proportion_realists'] = df_driver_extract['number_of_realists'] / df_driver_extract['number_of_students'] * 100
df_driver_extract['proportion_reinventors'] = df_driver_extract['number_of_reinventors'] / df_driver_extract['number_of_students'] * 100

##Divide posts and likes by number of stakeholders
df_driver_extract['posts_per_stakeholder'] = df_driver_extract['stakeholder_posts'] / df_driver_extract['number_of_stakeholders']
df_driver_extract['likes_per_stakeholder'] = df_driver_extract['stakeholder_likes'] / df_driver_extract['number_of_stakeholders']

##Divide student posts and likes by number of students
df_driver_extract['posts_per_student'] = df_driver_extract['student_posts'] / df_driver_extract['number_of_students']
df_driver_extract['likes_per_student'] = df_driver_extract['student_likes'] / df_driver_extract['number_of_students']

##Select columns for dataframe
df_driver_extract = df_driver_extract[['course_abbreviation',
                                       'course_type',
                                       'subject_vertical',
                                       'average_course_price',
                                       'average_course_grade',
                                       'posts_per_stakeholder',
                                       'likes_per_stakeholder',
                                       'posts_per_student',
                                       'likes_per_student',
                                       'proportion_aspirants',
                                       'proportion_dreamers',
                                       'proportion_leaders',
                                       'proportion_pros',
                                       'proportion_realists',
                                       'proportion_reinventors']]

##View dataframe
print(df_driver_extract.head(20))

##Join with corr courses dataframe
df_driver = pandas.merge(df_corr_courses, df_driver_extract, on='course_abbreviation')

##Drop course abbreviation
df_driver.drop(['course_abbreviation'], axis=1, inplace=True)
df_driver = df_driver.fillna(0)

##Rename R-squared to performance measure
df_driver = df_driver.rename(columns={'r_squared': 'performance_measure'})
print(df_driver.head(20))

##5.3) Calculate correlations with the performance measure

##Create a dataframe with the correlations with the performance measure
df_corr_perf_measure = pandas.DataFrame(df_driver.corr())
print(df_corr_perf_measure.head(20))

##Clean data and transform to R-squared value
df_corr_perf_measure = df_corr_perf_measure.reset_index()
df_corr_perf_measure = df_corr_perf_measure[['index', 'performance_measure']]
df_corr_perf_measure['performance_measure'] = df_corr_perf_measure['performance_measure'] ** 2
df_corr_perf_measure = df_corr_perf_measure.rename(columns={'index': 'drivers',
                                                            'performance_measure': 'r_squared'})
print(df_corr_perf_measure)

##5.4) Plot strong/weak correlations against performance measure
##Plot the strong/weak correlations
##Create figure object
fig_pros_vs_perf_measure = plotly.express.scatter(data_frame=df_driver,
                                                  x=df_driver['proportion_pros'],
                                                  y=df_driver['performance_measure'],
                                                  title='Proportion of Pros by Performance Measure',
                                                  trendline='ols',
                                                  trendline_color_override='red',
                                                  hover_data=['proportion_pros',
                                                              'performance_measure'],
                                                  labels={'proportion_pros': 'Proportion of Pros',
                                                          'performance_measure': 'Performance Measure'})

fig_pros_vs_perf_measure.show()

##Save figure
fig_pros_vs_perf_measure.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_pros_vs_perf_measure.png')

##Create figure object
fig_dreamers_vs_perf_measure = plotly.express.scatter(data_frame=df_driver,
                                                      x=df_driver['proportion_dreamers'],
                                                      y=df_driver['performance_measure'],
                                                      title='Proportion of Dreamers by Performance Measure',
                                                      trendline='ols',
                                                      trendline_color_override='red',
                                                      hover_data=['proportion_dreamers',
                                                                  'performance_measure'],
                                                      labels={'proportion_dreamers': 'Proportion of Dreamers',
                                                              'performance_measure': 'Performance Measure'})

fig_dreamers_vs_perf_measure.show()

##Save figure
fig_dreamers_vs_perf_measure.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_dreamers_vs_perf_measure.png')

##Create figure object
fig_posts_vs_perf_measure = plotly.express.scatter(data_frame=df_driver,
                                                   x=df_driver['posts_per_student'],
                                                   y=df_driver['performance_measure'],
                                                   title='Student Posts by Performance Measure',
                                                   trendline='ols',
                                                   trendline_color_override='red',
                                                   hover_data=['posts_per_student',
                                                               'performance_measure'],
                                                   labels={'posts_per_student': 'Posts per Student',
                                                           'performance_measure': 'Performance Measure'})

fig_posts_vs_perf_measure.show()

##Save figure
fig_posts_vs_perf_measure.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_posts_vs_perf_measure.png')

################################################################################################################################################################
#6.) ADDITIONAL NPS BY FINAL MARK

##6.1) Extract data
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT B.university,
       CONCAT(B.university_code, '-', B.course_abbreviation) AS course_abbreviation,
       A.vle_user_id,
       A.final_mark,
       E.npsscore
FROM rdw_bcd.vw_bcd_enrolment A
LEFT JOIN rdw_bcd.vw_bcd_registration B ON B.registration_id = A.registration_id
LEFT JOIN rdw_bcd.vw_bcd_presentation C ON C.presentation_code = A.presentation_code
LEFT JOIN rdw_bcd.vw_bcd_partner D ON D.vle_credential_id = C.vle_credential_id
                                   AND D.university_code = C.university_code
LEFT JOIN (SELECT university AS la_university,
                  course_id AS vle_course_id,
                  userid AS vle_user_id,
                  npsscore
           FROM rdw_la.vw_la_survey_summarrised
           WHERE npsscore IS NOT NULL) E ON E.la_university = D.la_university
                                         AND E.vle_course_id = A.vle_course_id
                                         AND E.vle_user_id = A.vle_user_id
WHERE C.product_life_cycle_status = 'Completed'
AND A.vle_user_id IS NOT NULL
AND A.vle_course_id IS NOT NULL
AND A.final_mark IS NOT NULL
AND E.npsscore IS NOT NULL
"""

##Create pandas dataframe
df_nps = pandas.read_sql_query(sql, rdw_conn)
print(df_nps.head(20))

##6.2) Clean data

##Drop columns with nulls
df_nps = df_nps.dropna(axis=0, how='any')
print(df_nps.head(20))

##6.3) Calculate correlation for different courses

##Calculate correlation for each course abbreviation
df_corr_nps = pandas.DataFrame(df_nps.groupby('course_abbreviation')[['final_mark', 'npsscore']].corr().iloc[0::2,-1]).reset_index()
df_corr_nps = df_corr_nps[['course_abbreviation', 'npsscore']]
df_corr_nps = df_corr_nps.rename(columns={'npsscore': 'r_squared'})
df_corr_nps['r_squared'] = df_corr_nps['r_squared'] ** 2
df_corr_nps = df_corr_nps.sort_values(by='r_squared', ascending=False)
print(df_corr_nps.head(20))
print(df_corr_nps.tail(20))

##6.4) Plot nps score by final grade
df_tec_lea = df_nps[df_nps['course_abbreviation'].str.contains('TEC-LEA')]

##Create figure object
fig_tec_lea = plotly.express.scatter(data_frame=df_nps,
                                     x=df_nps['npsscore'],
                                     y=df_nps['final_mark'],
                                     title='NPS Score by Final Mark',
                                     trendline='ols',
                                     trendline_color_override='red',
                                     hover_data=['final_mark',
                                                 'npsscore',
                                                 'course_abbreviation'],
                                     labels={'final_mark': 'Average Final Mark',
                                             'npsscore': 'NPS Score',
                                             'course_abbreviation': 'Course Abbreviation'}).show()

##Save figure
fig_tec_lea.write_image('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/fig_tec_lea.png')


################################################################################################################################################################
#7.) MODULE LEVEL ANALYSIS

##7.1) Extract data
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT A.university AS la_university,
       A.course_name AS presentation_abbreviation,
       A.course_id AS vle_course_id,
       A.course_module_id,
       A.module_name,
       A.activity_name,
       A.user_id AS vle_user_id,
       A.user_role,
       CONCAT(A.firstname, ' ', A.lastname) AS student_name,
       B.module_grade,
       SUM(all_posts) AS number_of_posts
FROM rdw_la.vw_master_alluser_activities A
LEFT JOIN rdw_la.vw_module_grades B ON B.user_id = A.user_id
                                    AND B.course_id = A.course_id
                                    AND B.course_module_id = A.course_module_id
WHERE A.activity_type IN ('hsuforum', 'forum')
AND A.user_role = 'student'
AND (LOWER(A.activity_name) LIKE '%discussion forum%' OR LOWER(A.activity_name) LIKE '%class-wide%')
AND LOWER(A.activity_name) NOT LIKE '%small-group%'
AND LOWER(A.activity_name) NOT LIKE '%small group%'
AND LOWER(A.activity_name) NOT LIKE '%graded%'
AND LOWER(A.activity_name) NOT LIKE '%practical exercise%'
AND LOWER(A.activity_name) NOT LIKE '%final assignment%'
AND LOWER(A.activity_name) NOT LIKE '%orientation%'
AND B.module_grade IS NOT NULL
GROUP BY A.university,
         A.course_name,
         A.course_id,
         A.course_module_id,
         A.module_name,
         A.activity_name,
         A.user_id,
         A.user_role,
         CONCAT(A.firstname, ' ', A.lastname),
         B.module_grade;
"""

##Create pandas dataframe
df_modules = pandas.read_sql_query(sql, rdw_conn)

##Concatenate two strings
df_modules['course_module'] = df_modules['presentation_abbreviation'].map(str) + ' ' + df_modules['module_name']

##2.2) Clean data
##Clean df_extract
df_modules = df_modules.fillna(0)
df_modules['module_grade'].values[df_modules['module_grade'].values > 100] = 100
print(df_modules.head(20))
print('Number of Total Students:', len(df_modules))

##Calculate correlation for each course abbreviation
df_corr_modules = pandas.DataFrame(df_modules.groupby('course_module')[['module_grade', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_modules = df_corr_modules[['course_module', 'number_of_posts']]
df_corr_modules = df_corr_modules.rename(columns={'number_of_posts': 'r_squared'})
df_corr_modules['r_squared'] = df_corr_modules['r_squared'] ** 2
df_corr_modules = df_corr_modules.sort_values(by='r_squared', ascending=False)


df_corr_modules.to_csv('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/test.csv')

################################################################################################################################################################
##10.) PRESENTATION MODULE LEVEL

##Presentation module level
##First do at student level to calculate correlations
##Then join correlations back to presentation module level

##10.1) Base table
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT A.university AS la_university,
       A.course_name AS presentation_abbreviation,
       A.course_id AS vle_course_id,
       A.course_module_id,
       A.module_name,
       ROUND(AVG(B.module_grade), 2) AS average_grade,
       SUM(all_posts) AS number_of_posts
FROM rdw_la.vw_master_alluser_activities A
LEFT JOIN rdw_la.vw_module_grades B ON B.user_id = A.user_id
                                    AND B.course_id = A.course_id
                                    AND B.course_module_id = A.course_module_id
WHERE A.activity_type IN ('hsuforum', 'forum')
AND A.user_role = 'student'
AND (LOWER(A.activity_name) LIKE '%forum%' OR LOWER(A.activity_name) LIKE '%discussion%')
AND LOWER(A.activity_name) NOT LIKE '%small-group%'
AND LOWER(A.activity_name) NOT LIKE '%small group%'
AND LOWER(A.activity_name) NOT LIKE '%graded%'
AND LOWER(A.activity_name) NOT LIKE '%practical exercise%'
AND LOWER(A.activity_name) NOT LIKE '%final assignment%'
AND LOWER(A.activity_name) NOT LIKE '%orientation%'
AND B.module_grade IS NOT NULL
GROUP BY A.university,
         A.course_name,
         A.course_id,
         A.course_module_id,
         A.module_name;
"""

##Create pandas dataframe
df_pres_mod_base = pandas.read_sql_query(sql, rdw_conn)
print(df_pres_mod_base.head(20))

##Concatenate two strings
df_pres_mod_base['presentation_module'] = df_pres_mod_base['presentation_abbreviation'].map(str) + ' ' + df_pres_mod_base['module_name']
print(df_pres_mod_base.head(20))

##Select specific columns
df_pres_mod_base = df_pres_mod_base[['presentation_module', 'number_of_posts', 'average_grade']]
print(df_pres_mod_base.head(20))

##Correlation creation
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT A.university AS la_university,
       A.course_name AS presentation_abbreviation,
       A.course_id AS vle_course_id,
       A.course_module_id,
       A.module_name,
       A.user_id AS vle_user_id,
       A.user_role,
       CONCAT(A.firstname, ' ', A.lastname) AS student_name,
       B.module_grade,
       SUM(all_posts) AS number_of_posts
FROM rdw_la.vw_master_alluser_activities A
LEFT JOIN rdw_la.vw_module_grades B ON B.user_id = A.user_id
                                    AND B.course_id = A.course_id
                                    AND B.course_module_id = A.course_module_id
WHERE A.activity_type IN ('hsuforum', 'forum')
AND A.user_role = 'student'
AND (LOWER(A.activity_name) LIKE '%forum%' OR LOWER(A.activity_name) LIKE '%discussion%')
AND LOWER(A.activity_name) NOT LIKE '%small-group%'
AND LOWER(A.activity_name) NOT LIKE '%small group%'
AND LOWER(A.activity_name) NOT LIKE '%graded%'
AND LOWER(A.activity_name) NOT LIKE '%practical exercise%'
AND LOWER(A.activity_name) NOT LIKE '%final assignment%'
AND LOWER(A.activity_name) NOT LIKE '%orientation%'
AND B.module_grade IS NOT NULL
GROUP BY A.university,
         A.course_name,
         A.course_id,
         A.course_module_id,
         A.module_nr_from_name,
         A.module_name,
         A.user_id,
         A.user_role,
         CONCAT(A.firstname, ' ', A.lastname),
         B.module_grade;
"""

##Create pandas dataframe
df_pres_mod = pandas.read_sql_query(sql, rdw_conn)

##Concatenate two strings
df_pres_mod['presentation_module'] = df_pres_mod['presentation_abbreviation'].map(str) + ' ' + df_pres_mod['module_name']

##Clean df_extract
df_pres_mod = df_pres_mod.fillna(0)
df_pres_mod['module_grade'].values[df_pres_mod['module_grade'].values > 100] = 100
print(df_pres_mod.head(20))

##Calculate correlation for each course abbreviation
df_corr_pres_mod = pandas.DataFrame(df_pres_mod.groupby('presentation_module')[['module_grade', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_pres_mod = df_corr_pres_mod[['presentation_module', 'number_of_posts']]
df_corr_pres_mod = df_corr_pres_mod.rename(columns={'number_of_posts': 'r_squared'})
df_corr_pres_mod['r_squared'] = df_corr_pres_mod['r_squared'] ** 2
df_corr_pres_mod = df_corr_pres_mod.sort_values(by='r_squared', ascending=False)
print(df_corr_pres_mod.head(20))

##Join to base table
df_pres_mod_final = pandas.merge(left=df_pres_mod_base, right=df_corr_pres_mod, how='inner')
print(df_pres_mod_final.head(20))

##Export to df_corr_sub_vertical
df_pres_mod_final.to_csv('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/df_pres_mod_final.csv')

################################################################################################################################################################
##11.) DATA SOURCE FOR COURSE MODULE

##Base table
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT CONCAT(SPLIT_PART(A.course_name, '-', 1), '-', SPLIT_PART(A.course_name, '-', 2)) AS course_abbreviation,
       A.module_nr_from_name,
       A.module_name,
       ROUND(AVG(B.module_grade), 2) AS average_grade,
       SUM(all_posts) AS number_of_posts
FROM rdw_la.vw_master_alluser_activities A
LEFT JOIN rdw_la.vw_module_grades B ON B.user_id = A.user_id
                                    AND B.course_id = A.course_id
                                    AND B.course_module_id = A.course_module_id
WHERE A.activity_type IN ('hsuforum', 'forum')
AND A.user_role = 'student'
AND (LOWER(A.activity_name) LIKE '%forum%' OR LOWER(A.activity_name) LIKE '%discussion%')
AND LOWER(A.activity_name) NOT LIKE '%small-group%'
AND LOWER(A.activity_name) NOT LIKE '%small group%'
AND LOWER(A.activity_name) NOT LIKE '%graded%'
AND LOWER(A.activity_name) NOT LIKE '%practical exercise%'
AND LOWER(A.activity_name) NOT LIKE '%final assignment%'
AND LOWER(A.activity_name) NOT LIKE '%orientation%'
AND B.module_grade IS NOT NULL
GROUP BY CONCAT(SPLIT_PART(A.course_name, '-', 1), '-', SPLIT_PART(A.course_name, '-', 2)),
         A.module_nr_from_name,
         A.module_name;
"""

##Create pandas dataframe
df_cour_mod_base = pandas.read_sql_query(sql, rdw_conn)
print(df_cour_mod_base.head(20))

##Concatenate two strings
df_cour_mod_base['course_module'] = df_cour_mod_base['course_abbreviation'].map(str) + ' ' + df_cour_mod_base['module_name']
print(df_cour_mod_base.head(20))

##Select specific columns
df_cour_mod_base = df_cour_mod_base[['course_module', 'number_of_posts', 'average_grade']]
print(df_cour_mod_base.head(20))

##Correlation creation
##Connect to database
rdw_conn = psycopg2.connect(user=config['USER_LA']['RDW_PROD'],
                            password=config['PWD_LA']['RDW_PROD'],
                            host=config['HOST']['RDW_STAG'],
                            database='rdw')

##Sql query
sql = """
SELECT CONCAT(SPLIT_PART(A.course_name, '-', 1), '-', SPLIT_PART(A.course_name, '-', 2)) AS course_abbreviation,
       A.module_name,
       A.module_nr_from_name,
       CONCAT(A.firstname, ' ', A.lastname) AS student_name,
       B.module_grade,
       SUM(all_posts) AS number_of_posts
FROM rdw_la.vw_master_alluser_activities A
LEFT JOIN rdw_la.vw_module_grades B ON B.user_id = A.user_id
                                    AND B.course_id = A.course_id
                                    AND B.course_module_id = A.course_module_id
WHERE A.activity_type IN ('hsuforum', 'forum')
AND A.user_role = 'student'
AND (LOWER(A.activity_name) LIKE '%forum%' OR LOWER(A.activity_name) LIKE '%discussion%')
AND LOWER(A.activity_name) NOT LIKE '%small-group%'
AND LOWER(A.activity_name) NOT LIKE '%small group%'
AND LOWER(A.activity_name) NOT LIKE '%graded%'
AND LOWER(A.activity_name) NOT LIKE '%practical exercise%'
AND LOWER(A.activity_name) NOT LIKE '%final assignment%'
AND LOWER(A.activity_name) NOT LIKE '%orientation%'
AND B.module_grade IS NOT NULL
GROUP BY CONCAT(SPLIT_PART(A.course_name, '-', 1), '-', SPLIT_PART(A.course_name, '-', 2)),
         A.module_name,
         A.module_nr_from_name,
         CONCAT(A.firstname, ' ', A.lastname),
         B.module_grade;
"""

##Create pandas dataframe
df_cour_mod = pandas.read_sql_query(sql, rdw_conn)

##Concatenate two strings
df_cour_mod['course_module'] = df_cour_mod['course_abbreviation'].map(str) + ' ' + df_cour_mod['module_name']

##Clean df_extract
df_cour_mod = df_cour_mod.fillna(0)
df_cour_mod['module_grade'].values[df_cour_mod['module_grade'].values > 100] = 100
print(df_cour_mod.head(20))

##Calculate correlation for each course abbreviation
df_corr_cour_mod = pandas.DataFrame(df_cour_mod.groupby('course_module')[['module_grade', 'number_of_posts']].corr().iloc[0::2,-1]).reset_index()

##Edit resulting dataframe
df_corr_cour_mod = df_corr_cour_mod[['course_module', 'number_of_posts']]
df_corr_cour_mod = df_corr_cour_mod.rename(columns={'number_of_posts': 'r_squared'})
df_corr_cour_mod['r_squared'] = df_corr_cour_mod['r_squared'] ** 2
df_corr_cour_mod = df_corr_cour_mod.sort_values(by='r_squared', ascending=False)
print(df_corr_cour_mod.head(20))

##Join to base table
df_cour_mod_final = pandas.merge(left=df_cour_mod_base, right=df_corr_cour_mod, how='inner')
print(df_cour_mod_final.head(20))

##Export to df_corr_sub_vertical
df_cour_mod_final.to_csv('/Users/jdeswardt/Documents/projects/discussion_forum_driver_analysis/df_cour_mod_final.csv')

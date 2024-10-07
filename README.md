Project description:
A content management system (CMS) designed for creating, managing, and publishing blog pages with a multi-role approval workflow. Key features include:

	•	HTML & Image Storage: Save and display HTML-based blog content and images.
	•	Approval Workflow: Writers submit content to group leaders, who approve or reject submissions. Admins provide final approval before publishing.
	•	Role-Based Access: Support for multiple roles (Writers, Leaders, Admins) with distinct responsibilities.
	•	Group Management: Users can be organized into groups, each with a leader responsible for content approval within the group.
	•	Content List: View and manage a list of all created HTML pages.

Perfect for teams that need structured content approval processes before publishing posts.


# Configuration for local development
1. create virtual environment
python3 -m venv venv
2. activate the environment 
  source ${pwd}/venv/bin/activate
4. create .env file and copy .env-example on it
5. intall dependencies
  pip install -r requirements.txt
7. run migration
  alembic upgrade head
9. start the server with uvicorn
  uvicorn app.main:app --reload
 - the server should be runing on http://127.0.0.1:8000
# conf for docker environment
1.modify variables on docker-compose.yml then run 
  docker-compose up

# important
for those who don't like to deal with alembic you can add this line to 
the main.py file:
  models.Base.metadata.create_all(bind=engine)
  just after the app instance 
  


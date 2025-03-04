import streamlit as st # type: ignore
import random
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
from datetime import datetime, timedelta
import json
import os
from PIL import Image # type: ignore
import requests # type: ignore
from urllib.parse import urlparse
from bs4 import BeautifulSoup # type: ignore
import time
import concurrent.futures
import plotly.graph_objects as go # type: ignore

# Set page configuration with custom theme
st.set_page_config(
    page_title="Growth Mindset & Project Tracker",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with improved styling
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 24px;
        border-radius: 5px;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    .project-card {
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin: 10px 0;
        background-color: white;
    }
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .url-example {
        background-color: #f8f9fa;
        padding: 5px;
        border-radius: 3px;
        font-family: monospace;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'projects' not in st.session_state:
    st.session_state.projects = []
if 'challenges_completed' not in st.session_state:
    st.session_state.challenges_completed = 0
if 'streak' not in st.session_state:
    st.session_state.streak = 0
if 'reflections' not in st.session_state:
    st.session_state.reflections = []

class ProjectTracker:
    def __init__(self):
        self.project_types = ["Web Development", "Data Science", "Mobile App", "Other"]
        
    def validate_vercel_url(self, url):
        """Validate if the URL is a proper web URL"""
        try:
            parsed = urlparse(url)
            # Accept any valid URL that contains either vercel.app or is a custom domain
            return all([parsed.scheme, parsed.netloc]) and (
                '.vercel.app' in url.lower() or  # Vercel default domain
                '.netlify.app' in url.lower() or  # Also accept Netlify
                url.startswith('https://') or     # Accept any HTTPS URL
                url.startswith('http://')         # Accept any HTTP URL
            )
        except:
            return False
    
    def add_project(self, name, url, project_type, description):
        if not name:
            return False, "Please enter a project name"
        
        if not url:
            return False, "Please enter a project URL"
        
        # Clean up URL
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        project = {
            "name": name,
            "url": url,
            "type": project_type,
            "description": description,
            "date_added": datetime.now().strftime("%Y-%m-%d"),
            "challenges": [],
            "learnings": []
        }
        st.session_state.projects.append(project)
        return True, "Project added successfully! 🎉"
    
    def add_project_update(self, project_index, challenge, learning):
        if 0 <= project_index < len(st.session_state.projects):
            st.session_state.projects[project_index]["challenges"].append(challenge)
            st.session_state.projects[project_index]["learnings"].append(learning)
            return True
        return False

    def analyze_projects(self):
        analyzer = ProjectAnalyzer()
        results = {}
        
        with st.spinner('Analyzing your projects...'):
            for project in st.session_state.projects:
                results[project['name']] = analyzer.analyze_url(project['url'])
        
        return results

class ProjectAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def clean_url(self, url):
        """Clean and format URL properly"""
        try:
            # Handle Vercel dashboard URLs
            if 'vercel.com' in url:
                # Extract project name from Vercel dashboard URL
                parts = url.split('/')
                for i, part in enumerate(parts):
                    if part == 'projects' and i + 1 < len(parts):
                        return f"https://{parts[i+1]}.vercel.app"
                    elif 'vercel.com' in part and i + 1 < len(parts):
                        return f"https://{parts[i+1]}.vercel.app"
            
            # Remove 'https://' or 'http://' if present
            url = url.replace('https://', '').replace('http://', '')
            
            # Remove any trailing slashes
            url = url.rstrip('/')
            
            # Add https:// prefix
            return f"https://{url}"
        except Exception as e:
            raise Exception(f"URL cleaning failed: {str(e)}")

    def analyze_url(self, url):
        """Analyze a project URL and return detailed insights"""
        try:
            # Clean the URL first
            cleaned_url = self.clean_url(url)
            st.info(f"Analyzing URL: {cleaned_url}")  # Show which URL is being analyzed
            
            try:
                response = requests.get(cleaned_url, headers=self.headers, timeout=10)
            except requests.exceptions.RequestException as e:
                # Try alternative URL formats if first attempt fails
                alternative_urls = [
                    f"https://{url.replace('https://', '').replace('http://', '')}",
                    f"http://{url.replace('https://', '').replace('http://', '')}",
                    url if url.startswith(('http://', 'https://')) else f"https://{url}"
                ]
                
                for alt_url in alternative_urls:
                    try:
                        st.info(f"Trying alternative URL: {alt_url}")
                        response = requests.get(alt_url, headers=self.headers, timeout=10)
                        cleaned_url = alt_url
                        break
                    except requests.exceptions.RequestException:
                        continue
                else:
                    raise Exception(
                        f"Could not connect to any URL variation. Please check if the project is deployed and accessible.\n"
                        f"Original URL: {url}\n"
                        f"Tried URLs: {[cleaned_url] + alternative_urls}"
                    )

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Detailed analysis
            analysis = {
                'basic_info': {
                    'url': cleaned_url,
                    'status': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'title': soup.title.string if soup.title else "No title found",
                },
                'seo': self._analyze_seo(soup),
                'technologies': self._detect_technologies(soup),
                'performance': self._analyze_performance(response),
                'security': self._analyze_security(response),
                'accessibility': self._analyze_accessibility(soup),
                'content': self._analyze_content(soup)
            }
            
            # Calculate overall score
            analysis['scores'] = self._calculate_scores(analysis)
            
            return analysis
            
        except Exception as e:
            return {
                'error': str(e),
                'suggestions': """
                Please try the following:
                1. Make sure your project is deployed and accessible
                2. Use the actual deployed URL (e.g., https://your-project.vercel.app)
                3. If using Vercel dashboard URL, use the deployment URL instead
                4. Check if the project is public and accessible
                
                Example valid URLs:
                ✅ https://your-project.vercel.app
                ✅ your-project.vercel.app
                ✅ https://your-custom-domain.com
                
                Invalid URLs:
                ❌ vercel.com/username/project-name (dashboard URLs)
                ❌ Internal project paths
                """
            }

    def _analyze_seo(self, soup):
        """Analyze SEO elements"""
        meta_desc = soup.find('meta', {'name': 'description'})
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        h1_tags = soup.find_all('h1')
        
        return {
            'meta_description': meta_desc.get('content') if meta_desc else None,
            'meta_keywords': meta_keywords.get('content') if meta_keywords else None,
            'h1_count': len(h1_tags),
            'has_robots_txt': 'robots' in str(soup).lower(),
            'has_sitemap': 'sitemap' in str(soup).lower(),
            'image_alt_texts': len([img for img in soup.find_all('img') if img.get('alt')])
        }

    def _detect_technologies(self, soup):
        """Detect technologies used"""
        page_text = str(soup).lower()
        technologies = {
            'frontend': [],
            'frameworks': [],
            'libraries': [],
            'analytics': []
        }
        
        # Frontend technologies
        if 'react' in page_text or 'jsx' in page_text:
            technologies['frontend'].append('React')
        if 'vue' in page_text:
            technologies['frontend'].append('Vue.js')
        if 'angular' in page_text:
            technologies['frontend'].append('Angular')
            
        # Frameworks
        if 'next' in page_text:
            technologies['frameworks'].append('Next.js')
        if 'nuxt' in page_text:
            technologies['frameworks'].append('Nuxt.js')
        if 'gatsby' in page_text:
            technologies['frameworks'].append('Gatsby')
            
        # Libraries
        if 'tailwind' in page_text:
            technologies['libraries'].append('Tailwind CSS')
        if 'bootstrap' in page_text:
            technologies['libraries'].append('Bootstrap')
        if 'jquery' in page_text:
            technologies['libraries'].append('jQuery')
            
        # Analytics
        if 'ga.js' in page_text or 'analytics' in page_text:
            technologies['analytics'].append('Google Analytics')
        
        return technologies

    def _analyze_performance(self, response):
        """Analyze performance metrics"""
        return {
            'page_size': len(response.content) / 1024,  # KB
            'load_time': response.elapsed.total_seconds(),
            'content_type': response.headers.get('content-type'),
            'compression': 'gzip' in response.headers.get('content-encoding', '').lower(),
            'cache_control': response.headers.get('cache-control', 'None')
        }

    def _analyze_security(self, response):
        """Analyze security headers"""
        headers = response.headers
        return {
            'has_https': response.url.startswith('https'),
            'has_hsts': 'strict-transport-security' in headers,
            'has_xss_protection': 'x-xss-protection' in headers,
            'has_content_security': 'content-security-policy' in headers,
            'has_x_frame_options': 'x-frame-options' in headers
        }

    def _analyze_accessibility(self, soup):
        """Analyze accessibility features"""
        return {
            'has_lang': bool(soup.find('html').get('lang')),
            'has_aria_labels': len([tag for tag in soup.find_all() if any(attr for attr in tag.attrs if 'aria-' in attr)]),
            'has_skip_links': 'skip' in str(soup).lower(),
            'form_labels': len(soup.find_all('label')),
            'image_alts': len([img for img in soup.find_all('img') if img.get('alt')])
        }

    def _analyze_content(self, soup):
        """Analyze content structure"""
        return {
            'word_count': len(str(soup.get_text()).split()),
            'headings': {
                'h1': len(soup.find_all('h1')),
                'h2': len(soup.find_all('h2')),
                'h3': len(soup.find_all('h3'))
            },
            'links': len(soup.find_all('a')),
            'images': len(soup.find_all('img')),
            'paragraphs': len(soup.find_all('p'))
        }

    def _calculate_scores(self, analysis):
        """Calculate scores for different aspects"""
        scores = {}
        
        # SEO Score (0-100)
        seo_score = 0
        seo = analysis['seo']
        if seo['meta_description']: seo_score += 20
        if seo['meta_keywords']: seo_score += 15
        if seo['h1_count'] == 1: seo_score += 15
        if seo['has_robots_txt']: seo_score += 15
        if seo['has_sitemap']: seo_score += 15
        if seo['image_alt_texts'] > 0: seo_score += 20
        scores['seo'] = seo_score
        
        # Performance Score (0-100)
        perf = analysis['performance']
        perf_score = 100
        if perf['load_time'] > 2: perf_score -= 30
        if perf['page_size'] > 5000: perf_score -= 30
        if not perf['compression']: perf_score -= 20
        scores['performance'] = max(0, perf_score)
        
        # Security Score (0-100)
        sec = analysis['security']
        sec_score = 0
        if sec['has_https']: sec_score += 30
        if sec['has_hsts']: sec_score += 20
        if sec['has_xss_protection']: sec_score += 20
        if sec['has_content_security']: sec_score += 15
        if sec['has_x_frame_options']: sec_score += 15
        scores['security'] = sec_score
        
        # Overall Score
        scores['overall'] = int((scores['seo'] + scores['performance'] + scores['security']) / 3)
        
        return scores

class GrowthAnalyzer:
    def __init__(self):
        self.skill_categories = {
            'frontend': {
                'React': 0,
                'Next.js': 0,
                'CSS/SCSS': 0,
                'JavaScript': 0,
                'TypeScript': 0,
                'Responsive Design': 0,
                'UI Frameworks': 0
            },
            'backend': {
                'API Integration': 0,
                'Database': 0,
                'Authentication': 0,
                'Server Management': 0
            },
            'deployment': {
                'Vercel': 0,
                'CI/CD': 0,
                'Environment Setup': 0
            }
        }
        
    def analyze_project_growth(self, url):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            page_content = str(soup).lower()
            
            skills = {
                'frontend': self._analyze_frontend(soup, page_content),
                'backend': self._analyze_backend(soup, page_content),
                'deployment': self._analyze_deployment(soup, page_content),
                'complexity': self._calculate_complexity(soup)
            }
            
            return skills
        except Exception as e:
            return {'error': str(e)}

    def _analyze_frontend(self, soup, content):
        skills = {}
        
        # React/Next.js Detection
        skills['React'] = 'react' in content or 'next' in content
        skills['Next.js'] = '__next' in content
        
        # CSS Analysis
        css_complexity = len(soup.find_all('style')) + len(soup.find_all('link', rel='stylesheet'))
        skills['CSS/SCSS'] = min(css_complexity * 20, 100)
        
        # JavaScript Analysis
        js_complexity = len(soup.find_all('script'))
        skills['JavaScript'] = min(js_complexity * 15, 100)
        
        # TypeScript Detection
        skills['TypeScript'] = '.tsx' in content or '.ts' in content
        
        # Responsive Design
        media_queries = 'media=' in content or '@media' in content
        viewport_meta = bool(soup.find('meta', {'name': 'viewport'}))
        skills['Responsive Design'] = 100 if media_queries and viewport_meta else 50 if media_queries else 0
        
        # UI Frameworks
        ui_frameworks = {
            'tailwind': 'Tailwind CSS',
            'bootstrap': 'Bootstrap',
            'material-ui': 'Material UI',
            'chakra': 'Chakra UI'
        }
        skills['UI Frameworks'] = any(fw in content for fw in ui_frameworks)
        
        return skills

    def _analyze_backend(self, soup, content):
        skills = {}
        
        # API Integration
        api_indicators = ['fetch', 'axios', 'api', 'graphql']
        skills['API Integration'] = any(ind in content for ind in api_indicators)
        
        # Database
        db_indicators = ['mongodb', 'postgresql', 'mysql', 'firebase', 'supabase']
        skills['Database'] = any(ind in content for ind in db_indicators)
        
        # Authentication
        auth_indicators = ['auth', 'login', 'signup', 'jwt', 'session']
        skills['Authentication'] = any(ind in content for ind in auth_indicators)
        
        # Server Management
        server_indicators = ['express', 'node', 'server', 'middleware']
        skills['Server Management'] = any(ind in content for ind in server_indicators)
        
        return skills

    def _analyze_deployment(self, soup, content):
        skills = {}
        
        # Vercel Detection
        skills['Vercel'] = 'vercel' in content or '.vercel.app' in content
        
        # CI/CD
        cicd_indicators = ['github actions', 'travis', 'jenkins', 'gitlab-ci']
        skills['CI/CD'] = any(ind in content for ind in cicd_indicators)
        
        # Environment Setup
        env_indicators = ['.env', 'process.env', 'environment variables']
        skills['Environment Setup'] = any(ind in content for ind in env_indicators)
        
        return skills

    def _calculate_complexity(self, soup):
        # Calculate project complexity based on various factors
        factors = {
            'components': len(soup.find_all(['div', 'section', 'article'])),
            'scripts': len(soup.find_all('script')),
            'styles': len(soup.find_all('style')),
            'forms': len(soup.find_all('form')),
            'interactive': len(soup.find_all(['button', 'input', 'select'])),
            'images': len(soup.find_all('img')),
            'links': len(soup.find_all('a'))
        }
        
        complexity_score = sum([
            factors['components'] * 0.1,
            factors['scripts'] * 0.3,
            factors['styles'] * 0.2,
            factors['forms'] * 0.5,
            factors['interactive'] * 0.3,
            factors['images'] * 0.1,
            factors['links'] * 0.1
        ])
        
        return min(complexity_score, 100)

class GrowthDashboard:
    def show_growth_dashboard(self, projects):
        st.header("🚀 Your Growth Dashboard")
        
        if not projects:
            st.info("Add some projects to see your growth analysis!")
            return
        
        analyzer = GrowthAnalyzer()
        growth_data = []
        
        # Analyze each project
        with st.spinner("Analyzing your projects..."):
            for project in projects:
                analysis = analyzer.analyze_project_growth(project['url'])
                if 'error' not in analysis:
                    analysis['project_name'] = project['name']
                    analysis['date'] = project['date_added']
                    growth_data.append(analysis)
        
        if growth_data:
            self._show_skill_progress(growth_data)
            self._show_project_complexity(growth_data)
            self._show_growth_insights(growth_data)
            self._show_recommendations(growth_data)

    def _show_skill_progress(self, growth_data):
        st.subheader("💪 Skill Progress")
        
        # Calculate skill levels across projects
        skills = {
            'Frontend': ['React', 'Next.js', 'CSS/SCSS', 'JavaScript', 'TypeScript'],
            'Backend': ['API Integration', 'Database', 'Authentication'],
            'Deployment': ['Vercel', 'CI/CD', 'Environment Setup']
        }
        
        tabs = st.tabs(list(skills.keys()))
        
        for tab, (category, skill_list) in zip(tabs, skills.items()):
            with tab:
                skill_progress = []
                for skill in skill_list:
                    # Calculate progress for each skill
                    progress = sum(1 for data in growth_data 
                                 if data[category.lower()].get(skill, False)) / len(growth_data) * 100
                    skill_progress.append({'Skill': skill, 'Progress': progress})
                
                df = pd.DataFrame(skill_progress)
                fig = px.bar(df, x='Skill', y='Progress',
                           title=f'{category} Skills Progress',
                           labels={'Progress': 'Mastery Level (%)'})
                st.plotly_chart(fig)

    def _show_project_complexity(self, growth_data):
        st.subheader("📈 Project Complexity Over Time")
        
        df = pd.DataFrame([{
            'Project': data['project_name'],
            'Date': data['date'],
            'Complexity': data['complexity']
        } for data in growth_data])
        
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        
        fig = px.line(df, x='Date', y='Complexity',
                     title='Project Complexity Trend',
                     labels={'Complexity': 'Complexity Score'})
        st.plotly_chart(fig)

    def _show_growth_insights(self, growth_data):
        st.subheader("🎯 Growth Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Calculate total skills mastered
            total_skills = sum(1 for data in growth_data[-1].items() 
                             if isinstance(data[1], bool) and data[1])
            st.metric("Skills Mastered", total_skills)
            
            # Calculate growth rate
            if len(growth_data) > 1:
                first_complexity = growth_data[0]['complexity']
                last_complexity = growth_data[-1]['complexity']
                growth_rate = ((last_complexity - first_complexity) / first_complexity) * 100
                st.metric("Growth Rate", f"{growth_rate:.1f}%")
        
        with col2:
            # Project count
            st.metric("Total Projects", len(growth_data))
            
            # Calculate consistency
            dates = [datetime.strptime(data['date'], '%Y-%m-%d') for data in growth_data]
            if len(dates) > 1:
                avg_days = (max(dates) - min(dates)).days / (len(dates) - 1)
                consistency = max(0, 100 - (avg_days - 7) * 5)  # Reduce score for gaps > 7 days
                st.metric("Consistency Score", f"{consistency:.1f}%")

    def _show_recommendations(self, growth_data):
        st.subheader("💡 Growth Recommendations")
        
        latest_data = growth_data[-1]
        
        # Identify areas for improvement
        recommendations = []
        
        # Frontend recommendations
        if not latest_data['frontend']['TypeScript']:
            recommendations.append("Consider learning TypeScript for better code quality")
        if not latest_data['frontend']['Next.js']:
            recommendations.append("Explore Next.js for better React applications")
        
        # Backend recommendations
        if not latest_data['backend']['Database']:
            recommendations.append("Add database integration to your projects")
        if not latest_data['backend']['Authentication']:
            recommendations.append("Implement user authentication in your next project")
        
        # Deployment recommendations
        if not latest_data['deployment']['CI/CD']:
            recommendations.append("Set up CI/CD pipelines for automated deployment")
        
        # Display recommendations
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f"{i}. {rec}")
        
        if not recommendations:
            st.success("Great job! You're implementing many best practices. Keep exploring new technologies!")

class GrowthMindsetApp:
    def __init__(self):
        self.project_tracker = ProjectTracker()
        self.growth_dashboard = GrowthDashboard()
        self.quotes = [
            "The more that you learn, the more places you'll go. - Dr. Seuss",
            "Mistakes are proof that you're trying.",
            "Everything is hard before it is easy. - Goethe",
            "The expert in anything was once a beginner.",
            "Growth is a process. Results are not immediate but they are inevitable with consistent effort.",
            "Your potential is unlimited. Go for it!",
            "Challenge yourself to be uncomfortable.",
            "The only person you should try to be better than is who you were yesterday."
        ]

    def show_header(self):
        st.title("🚀 Project Growth Tracker")
        st.markdown("""
        <div style='text-align: center'>
            Track your projects, document challenges, and monitor your growth journey!
        </div>
        """, unsafe_allow_html=True)

    def show_project_manager(self):
        st.header("🎯 Project Manager")
        
        # Add new project
        with st.expander("Add New Project", expanded=True):
            st.markdown("""
            ### 📝 Add Your Project Details
            Track your deployed projects and document your learning journey.
            """)
            
            with st.form("new_project"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Project Name")
                    url = st.text_input("Project URL", 
                        help="Enter the URL where your project is deployed")
                with col2:
                    project_type = st.selectbox("Project Type", self.project_tracker.project_types)
                    description = st.text_area("Project Description")
                
                # URL Examples and Guidelines
                st.markdown("""
                #### 🔗 Valid URL Examples:
                """)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    - <span class='url-example'>https://your-project.vercel.app</span>
                    - <span class='url-example'>https://your-custom-domain.com</span>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown("""
                    - <span class='url-example'>http://localhost:3000</span>
                    - <span class='url-example'>https://your-project.netlify.app</span>
                    """, unsafe_allow_html=True)
                
                if st.form_submit_button("Add Project"):
                    success, message = self.project_tracker.add_project(name, url, project_type, description)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        # Display projects
        if st.session_state.projects:
            st.markdown("### 📚 Your Projects")
            for idx, project in enumerate(st.session_state.projects):
                with st.container():
                    st.markdown(f"""
                    <div class="project-card">
                        <h3>{project['name']}</h3>
                        <p><strong>Type:</strong> {project['type']}</p>
                        <p><strong>URL:</strong> <a href="{project['url']}" target="_blank">{project['url']}</a></p>
                        <p><strong>Description:</strong> {project['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Project updates
                    with st.expander(f"📝 Add Update for {project['name']}"):
                        with st.form(f"update_project_{idx}"):
                            challenge = st.text_area("What challenges did you face?")
                            learning = st.text_area("What did you learn from these challenges?")
                            if st.form_submit_button("Save Update"):
                                project['challenges'].append(challenge)
                                project['learnings'].append(learning)
                                st.success("Update saved successfully! 🎉")
                    
                    # Show project history
                    if project['challenges']:
                        with st.expander("📋 View Project History"):
                            for c, l in zip(project['challenges'], project['learnings']):
                                st.markdown(f"""
                                ---
                                **Challenge:** {c}
                                
                                **Learning:** {l}
                                """)

    def show_analytics(self):
        st.header("📊 Growth Analytics")
        
        if st.session_state.projects:
            # Project type distribution
            project_types = {}
            for p in st.session_state.projects:
                project_types[p['type']] = project_types.get(p['type'], 0) + 1
            
            df_types = pd.DataFrame(list(project_types.items()), 
                                  columns=['Project Type', 'Count'])
            
            fig1 = px.pie(df_types, values='Count', names='Project Type',
                         title="Project Distribution by Type")
            st.plotly_chart(fig1)
            
            # Challenges over time
            challenge_data = []
            for project in st.session_state.projects:
                challenge_data.append({
                    'date': project['date_added'],
                    'challenges': len(project['challenges'])
                })
            
            if challenge_data:
                df_challenges = pd.DataFrame(challenge_data)
                df_challenges['date'] = pd.to_datetime(df_challenges['date'])
                df_challenges = df_challenges.sort_values('date')
                
                fig2 = px.line(df_challenges, x='date', y='challenges',
                              title='Challenges Tackled Over Time')
                st.plotly_chart(fig2)
        else:
            st.info("Add some projects to see your analytics!")

    def show_project_analysis(self):
        st.header("🔍 Project Analysis Dashboard")
        
        if not st.session_state.projects:
            st.info("Add some projects to see analysis!")
            return
        
        # Project selection
        project_names = [p['name'] for p in st.session_state.projects]
        selected_project = st.selectbox("Select Project to Analyze", project_names)
        
        # Show current URL
        project = next(p for p in st.session_state.projects if p['name'] == selected_project)
        st.write(f"Project URL: `{project['url']}`")
        
        # Add URL editing capability
        new_url = st.text_input("Edit URL (optional)", value=project['url'])
        if new_url != project['url']:
            if st.button("Update URL"):
                project['url'] = new_url
                st.success("URL updated successfully!")
                st.rerun()
        
        if st.button("Analyze Project"):
            with st.spinner(f"Analyzing {selected_project}..."):
                analyzer = ProjectAnalyzer()
                try:
                    # Show the URL being analyzed
                    cleaned_url = analyzer.clean_url(project['url'])
                    st.info(f"Analyzing URL: {cleaned_url}")
                    
                    analysis = analyzer.analyze_url(project['url'])
                    
                    if 'error' in analysis:
                        st.error(f"Analysis Error: {analysis['error']}")
                        st.markdown("### 💡 Suggestions:")
                        st.markdown(analysis.get('suggestions', ''))
                        return
                    
                    # Display Analysis Results
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Overall Score", f"{analysis['scores']['overall']}%")
                    with col2:
                        st.metric("SEO Score", f"{analysis['scores']['seo']}%")
                    with col3:
                        st.metric("Performance Score", f"{analysis['scores']['performance']}%")
                    with col4:
                        st.metric("Security Score", f"{analysis['scores']['security']}%")
                    
                    # Detailed Analysis Tabs
                    tabs = st.tabs(["Technologies", "Performance", "SEO", "Security", "Content", "Recommendations"])
                    
                    with tabs[0]:
                        st.subheader("🛠️ Technology Stack")
                        tech = analysis['technologies']
                        
                        if tech['frontend']:
                            st.write("**Frontend:**", ", ".join(tech['frontend']))
                        if tech['frameworks']:
                            st.write("**Frameworks:**", ", ".join(tech['frameworks']))
                        if tech['libraries']:
                            st.write("**Libraries:**", ", ".join(tech['libraries']))
                        if tech['analytics']:
                            st.write("**Analytics:**", ", ".join(tech['analytics']))
                    
                    with tabs[1]:
                        st.subheader("⚡ Performance Metrics")
                        perf = analysis['performance']
                        st.write(f"**Load Time:** {perf['load_time']:.2f} seconds")
                        st.write(f"**Page Size:** {perf['page_size']:.1f} KB")
                        st.write(f"**Compression:** {'Enabled' if perf['compression'] else 'Disabled'}")
                        st.write(f"**Cache Control:** {perf['cache_control']}")
                    
                    with tabs[2]:
                        st.subheader("🎯 SEO Analysis")
                        seo = analysis['seo']
                        st.write(f"**Meta Description:** {seo['meta_description'] or 'Missing'}")
                        st.write(f"**Meta Keywords:** {seo['meta_keywords'] or 'Missing'}")
                        st.write(f"**H1 Tags:** {seo['h1_count']}")
                        st.write(f"**Images with Alt Text:** {seo['image_alt_texts']}")
                    
                    with tabs[3]:
                        st.subheader("🔒 Security Analysis")
                        sec = analysis['security']
                        for key, value in sec.items():
                            st.write(f"**{key.replace('_', ' ').title()}:** {'✅' if value else '❌'}")
                    
                    with tabs[4]:
                        st.subheader("📝 Content Analysis")
                        content = analysis['content']
                        st.write(f"**Word Count:** {content['word_count']}")
                        st.write("**Heading Structure:**")
                        for h_type, count in content['headings'].items():
                            st.write(f"- {h_type.upper()}: {count}")
                        st.write(f"**Links:** {content['links']}")
                        st.write(f"**Images:** {content['images']}")
                        st.write(f"**Paragraphs:** {content['paragraphs']}")
                    
                    with tabs[5]:
                        st.subheader("💡 Recommendations")
                        recommendations = []
                        
                        # Performance recommendations
                        if analysis['performance']['load_time'] > 2:
                            recommendations.append("⚡ Optimize page load time (current: {:.2f}s)".format(
                                analysis['performance']['load_time']))
                        if not analysis['performance']['compression']:
                            recommendations.append("📦 Enable GZIP compression")
                        
                        # SEO recommendations
                        if not analysis['seo']['meta_description']:
                            recommendations.append("🎯 Add meta description")
                        if analysis['seo']['h1_count'] != 1:
                            recommendations.append("📝 Ensure exactly one H1 tag")
                        
                        # Security recommendations
                        if not analysis['security']['has_https']:
                            recommendations.append("🔒 Enable HTTPS")
                        if not analysis['security']['has_content_security']:
                            recommendations.append("🛡️ Add Content Security Policy")
                        
                        if recommendations:
                            for rec in recommendations:
                                st.markdown(f"- {rec}")
                        else:
                            st.success("Your project follows best practices! Keep up the good work!")

                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")
                    st.markdown("""
                    ### 💡 Troubleshooting:
                    1. Make sure your project is deployed and accessible
                    2. Use the actual deployed URL
                    3. Check if the project is public
                    4. Try updating the URL if it's incorrect
                    """)

    def run(self):
        self.show_header()
        
        # Sidebar
        st.sidebar.markdown("### 🧭 Navigation")
        page = st.sidebar.radio("", ["Project Manager", "Growth Dashboard", "Project Analysis"])
        
        # Random quote in sidebar
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 💭 Today's Inspiration")
        st.sidebar.info(random.choice(self.quotes))
        
        # Main content
        if page == "Project Manager":
            self.show_project_manager()
        elif page == "Growth Dashboard":
            self.growth_dashboard.show_growth_dashboard(st.session_state.projects)
        else:
            self.show_project_analysis()

    def show_resources(self):
        st.header("📚 Learning Resources")
        
        tabs = st.tabs(["Web Development", "Project Management", "Growth Mindset"])
        
        with tabs[0]:
            st.subheader("Web Development Resources")
            st.markdown("""
            - [Vercel Documentation](https://vercel.com/docs)
            - [Next.js Learning Guide](https://nextjs.org/learn)
            - [React Documentation](https://reactjs.org/docs/getting-started.html)
            """)
            
        with tabs[1]:
            st.subheader("Project Management Tips")
            st.markdown("""
            1. Break down large projects into smaller tasks
            2. Set realistic deadlines
            3. Document your challenges and solutions
            4. Regular code reviews and updates
            5. Track your progress consistently
            """)
            
        with tabs[2]:
            st.subheader("Growth Mindset Resources")
            st.markdown("""
            - **Books:**
              - "Mindset: The New Psychology of Success" by Carol S. Dweck
              - "Atomic Habits" by James Clear
            
            - **Videos:**
              - [The Power of Believing You Can Improve](https://www.ted.com/talks/carol_dweck_the_power_of_believing_that_you_can_improve)
            """)

if __name__ == "__main__":
    app = GrowthMindsetApp()
    app.run()
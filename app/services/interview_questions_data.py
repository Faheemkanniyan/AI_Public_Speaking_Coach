"""
Curated, high-quality question bank for SpeakPro AI Mock Interviews.
Generates structured, realistic interview questions tailored to interview types,
domains, technologies, and difficulty levels WITHOUT calling the Gemini API.
"""

from typing import List, Dict, Any
import random

# =====================================================================
# HR & BEHAVIORAL QUESTIONS
# =====================================================================

HR_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question": "Tell me about yourself and walk me through your background.",
        "difficulty": "Beginner",
        "question_type": "Behavioral",
        "expected_points": [
            "Concise professional summary",
            "Key technical or academic achievements",
            "Relevant project or work experiences",
            "Motivation and enthusiasm for this role"
        ],
        "ideal_answer": "I have a strong background in software engineering, focusing on building scalable web applications. Recently, I've worked on backend architecture and API performance, leading projects that delivered measurable business value. I am excited about this role because it aligns with my passion for building impactful products and continuous learning.",
        "evaluation_criteria": ["Clarity and structure", "Confidence and tone", "Relevance of highlights"]
    },
    {
        "question": "What are your greatest professional strengths, and what is an area you are actively working to improve?",
        "difficulty": "Beginner",
        "question_type": "Behavioral",
        "expected_points": [
            "Specific, relevant strengths with brief evidence",
            "Genuine, constructive weakness or growth area",
            "Concrete proactive actions taken to improve",
            "Self-awareness and positive attitude"
        ],
        "ideal_answer": "One of my greatest strengths is technical problem-solving and rapid learning of new tools. In terms of improvement, I used to struggle with delegating tasks when deadlines were tight. To address this, I started using structured task tracking and regular team check-ins, which significantly improved our collective throughput.",
        "evaluation_criteria": ["Self-awareness", "Credibility of examples", "Action-oriented mindset"]
    },
    {
        "question": "Why are you interested in joining our organization, and where do you see your career heading in the next 3 to 5 years?",
        "difficulty": "Intermediate",
        "question_type": "Behavioral",
        "expected_points": [
            "Clear understanding of company mission or tech stack",
            "Alignment between personal goals and company vision",
            "Realistic milestones for career progression",
            "Desire to take on greater ownership and mentorship"
        ],
        "ideal_answer": "I admire your team's commitment to engineering excellence and user-centric product innovation. Over the next 3 to 5 years, I envision developing deep domain expertise, taking ownership of critical architectural components, and mentoring junior engineers while driving tangible business impact.",
        "evaluation_criteria": ["Company alignment", "Long-term vision", "Professional ambition"]
    },
    {
        "question": "How do you handle high-pressure situations or competing, tight deadlines?",
        "difficulty": "Intermediate",
        "question_type": "Behavioral",
        "expected_points": [
            "Structured prioritization and task triage",
            "Proactive communication with stakeholders",
            "Maintaining emotional composure and focus",
            "Knowing when to ask for help or negotiate scope"
        ],
        "ideal_answer": "When facing tight deadlines, I immediately triage tasks by business impact and urgency. I communicate transparently with product managers and teammates about milestones and potential trade-offs. By breaking down complex deliverables into manageable daily goals and keeping stakeholders informed, I deliver reliable results without sacrificing code quality.",
        "evaluation_criteria": ["Prioritization strategy", "Stakeholder communication", "Resilience"]
    },
    {
        "question": "Describe a situation where you had a disagreement with a team member or manager. How did you resolve it?",
        "difficulty": "Advanced",
        "question_type": "Behavioral",
        "expected_points": [
            "Objective situation context",
            "Listening to the other perspective without defensiveness",
            "Focusing on data, user impact, and shared goals",
            "Constructive compromise or committing to the team decision"
        ],
        "ideal_answer": "During an API design phase, a colleague and I disagreed on whether to use GraphQL or REST. Instead of debating preferences, we set up an objective benchmark comparing payload size, caching requirements, and client implementation speed. The data showed REST was better suited for our mobile client constraints, so we aligned behind it and shipped the service ahead of schedule.",
        "evaluation_criteria": ["Conflict resolution skills", "Empathy and listening", "Data-driven alignment"]
    },
    {
        "question": "Tell me about a time you made a significant mistake at work or on a project. How did you handle it, and what did you learn?",
        "difficulty": "Advanced",
        "question_type": "Behavioral",
        "expected_points": [
            "Honest ownership without blame-shifting",
            "Immediate containment and communication",
            "Root-cause analysis and preventative measures",
            "Long-term lessons learned"
        ],
        "ideal_answer": "Early in my career, I deployed a database migration that locked a production table, causing transient timeouts. I immediately notified the team, rolled back the change, and restored service within minutes. Afterward, I conducted a blameless post-mortem, created zero-downtime migration guidelines, and added staging load tests to ensure it would never happen again.",
        "evaluation_criteria": ["Accountability", "Composure in crisis", "Systemic learning"]
    }
]

BEHAVIORAL_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question": "Using the STAR method, describe a challenging technical problem you solved.",
        "difficulty": "Intermediate",
        "question_type": "STAR Scenario",
        "expected_points": [
            "Situation: Context and business/technical stakes",
            "Task: What you specifically were responsible for",
            "Action: Concrete technical steps, debugging, or design choices",
            "Result: Quantifiable outcome or lesson learned"
        ],
        "ideal_answer": "In our payment processing system, API response times degraded to over 3 seconds under peak traffic. As the lead engineer, my task was to reduce latency below 400 milliseconds. I profiled the database queries, identified missing compound indexes, and implemented a Redis caching layer for idempotent requests. As a result, p99 latency dropped to 180 milliseconds and system throughput increased by 300%.",
        "evaluation_criteria": ["STAR structure fidelity", "Technical depth", "Quantifiable results"]
    },
    {
        "question": "Tell me about a time you had to adapt quickly to unexpected changes in project requirements.",
        "difficulty": "Intermediate",
        "question_type": "STAR Scenario",
        "expected_points": [
            "Nature of the sudden pivot or requirement change",
            "Flexibility and problem-solving attitude",
            "Re-planning and technical adjustments made",
            "Successful delivery under the new parameters"
        ],
        "ideal_answer": "Two weeks before product launch, our client requested support for real-time WebSocket notifications instead of polling. I re-evaluated our architecture, refactored our notification service into modular pub/sub consumers, and collaborated closely with the frontend team to integrate the new events. We launched on time with full real-time capabilities and high customer satisfaction.",
        "evaluation_criteria": ["Adaptability", "Collaboration", "Execution under uncertainty"]
    },
    {
        "question": "Describe an occasion where you took initiative to improve an existing process or codebase without being asked.",
        "difficulty": "Advanced",
        "question_type": "STAR Scenario",
        "expected_points": [
            "Identifying the inefficiency or tech debt",
            "Proactively researching and implementing the improvement",
            "Getting buy-in from teammates or leadership",
            "Measurable impact on productivity or stability"
        ],
        "ideal_answer": "I noticed our CI/CD pipeline took over 35 minutes to run, bottlenecking daily deployments. On my own initiative, I parallelized test suites, implemented Docker layer caching, and optimized dependency installations. This cut build times to 8 minutes, saving the engineering team hundreds of collective hours each month.",
        "evaluation_criteria": ["Proactiveness", "Technical initiative", "Measurable productivity gain"]
    }
]

# =====================================================================
# TECHNICAL QUESTIONS ORGANIZED BY TOPIC & DIFFICULTY
# =====================================================================

TOPIC_QUESTIONS: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "python": {
        "Beginner": [
            {
                "question": "Explain the difference between mutable and immutable data types in Python with examples.",
                "expected_points": [
                    "Definition of mutable vs immutable",
                    "Examples of immutable types (int, str, tuple, frozenset)",
                    "Examples of mutable types (list, dict, set)",
                    "Memory and performance implications"
                ],
                "ideal_answer": "In Python, immutable objects cannot have their state modified after creation, whereas mutable objects can be modified in-place. Integers, strings, and tuples are immutable; any modification creates a new object in memory. Lists, dictionaries, and sets are mutable, meaning elements can be added, updated, or removed without changing the object's memory address.",
                "evaluation_criteria": ["Conceptual accuracy", "Correct examples", "Memory understanding"]
            },
            {
                "question": "What is the difference between lists and tuples in Python, and when would you choose one over the other?",
                "expected_points": [
                    "Mutability difference (lists mutable, tuples immutable)",
                    "Syntax differences ([ ] vs ( ))",
                    "Tuples can be used as dictionary keys if elements are hashable",
                    "Tuples offer slight memory and performance advantages"
                ],
                "ideal_answer": "Lists are mutable sequences defined with square brackets, making them ideal for dynamic collections that change over time. Tuples are immutable sequences defined with parentheses. You choose tuples when data should remain constant, when you need hashable dictionary keys, or to benefit from slight performance and memory optimizations.",
                "evaluation_criteria": ["Clear contrast", "Use case clarity", "Hashability mention"]
            },
            {
                "question": "How does Python handle memory management and garbage collection?",
                "expected_points": [
                    "Reference counting as primary mechanism",
                    "Generational cyclic garbage collector (gc module)",
                    "Cycles detection (generational tracking Gen 0, 1, 2)",
                    "Python memory allocator (PyMalloc / private heap)"
                ],
                "ideal_answer": "Python primarily manages memory through reference counting, where every object tracks how many references point to it. When an object's reference count drops to zero, its memory is immediately deallocated. To resolve circular references that reference counting misses, Python uses a generational garbage collector that inspects three generations of objects periodically.",
                "evaluation_criteria": ["Reference counting", "Cycle detection", "Generational GC"]
            },
            {
                "question": "What are list comprehensions in Python and what are their benefits over traditional loops?",
                "expected_points": [
                    "Concise, readable syntax for creating lists",
                    "Inclusion of filtering conditions (if clauses)",
                    "Executed in optimized C bytecode for faster execution",
                    "When to avoid them for complex or nested logic"
                ],
                "ideal_answer": "List comprehensions provide a concise and expressive syntax for constructing lists from existing iterables. They combine mapping and filtering into a single readable line. Beyond brevity, they are typically faster than traditional for-loops because the iteration is executed at C speed within the Python interpreter.",
                "evaluation_criteria": ["Syntax mastery", "Performance rationale", "Readability guidelines"]
            },
            {
                "question": "Explain the difference between the 'is' operator and the '==' operator in Python.",
                "expected_points": [
                    "'==' checks value equality (calls __eq__)",
                    "'is' checks identity equality (object memory address id())",
                    "Common pitfall with integer caching / string interning",
                    "Correct use of 'is' with None, True, False"
                ],
                "ideal_answer": "The '==' operator checks value equality, determining whether two objects have identical contents by invoking their __eq__ method. The 'is' operator checks reference identity, confirming whether both variables point to the exact same location in memory using id(). 'is' should always be used when comparing against singletons like None.",
                "evaluation_criteria": ["Identity vs value", "Dunder method knowledge", "Singleton best practice"]
            }
        ],
        "Intermediate": [
            {
                "question": "Explain Python generators, the 'yield' statement, and how they optimize memory usage.",
                "expected_points": [
                    "Generators return an iterator and maintain state between yields",
                    "Lazy evaluation (values produced one at a time on-demand)",
                    "Dramatically lower memory consumption for large datasets",
                    "Generator functions vs generator expressions"
                ],
                "ideal_answer": "Generators are special functions that produce a sequence of values lazily using the 'yield' keyword instead of 'return'. When yield is encountered, execution pauses and local state is preserved until the next value is requested. This provides massive memory efficiency because large datasets do not need to be loaded into RAM simultaneously.",
                "evaluation_criteria": ["Lazy evaluation", "Memory efficiency", "State preservation"]
            },
            {
                "question": "What are decorators in Python, and how do you write a custom decorator that accepts arguments?",
                "expected_points": [
                    "Decorators wrap functions to modify or extend behavior without altering source code",
                    "Functions are first-class citizens in Python",
                    "Writing a three-level nested function to accept decorator arguments",
                    "Using functools.wraps to preserve original function metadata"
                ],
                "ideal_answer": "Decorators are higher-order functions that take a function as input and return a modified version, leveraging the fact that functions in Python are first-class citizens. To create a decorator that accepts arguments, you define an outer function taking the arguments, which returns the actual decorator, which in turn returns the wrapper function. You should always use @functools.wraps to preserve the decorated function's name and docstring.",
                "evaluation_criteria": ["Higher-order functions", "functools.wraps", "Nested closure structure"]
            },
            {
                "question": "Explain the Global Interpreter Lock (GIL) in Python and its impact on multithreading vs multiprocessing.",
                "expected_points": [
                    "GIL is a mutex that prevents multiple native threads from executing Python bytecode simultaneously",
                    "Impact on CPU-bound tasks (threading does not provide parallelism)",
                    "I/O-bound tasks still benefit from multithreading because GIL is released during I/O",
                    "Multiprocessing bypasses the GIL by creating separate processes with independent memory"
                ],
                "ideal_answer": "The Global Interpreter Lock (GIL) is a mutex in CPython that ensures only one thread executes Python bytecode at any given moment, simplifying memory management and C extensions. For CPU-bound tasks, multithreading cannot achieve true multi-core parallelism due to the GIL; multiprocessing is required instead. However, for I/O-bound tasks, multithreading remains effective because the GIL is released during network and disk I/O.",
                "evaluation_criteria": ["CPython internals", "CPU vs I/O bound", "Threading vs Multiprocessing"]
            },
            {
                "question": "Explain the difference between shallow copy and deep copy in Python with practical examples.",
                "expected_points": [
                    "Shallow copy copies the outer container, but references nested objects",
                    "Deep copy recursively duplicates all nested objects and references",
                    "The 'copy' module (copy.copy vs copy.deepcopy)",
                    "Mutating nested structures in shallow copies alters the original"
                ],
                "ideal_answer": "A shallow copy creates a new outer collection, but populates it with references to the child objects found in the original. If you mutate a nested list inside a shallow copy, the original object is also modified. A deep copy recursively copies both the outer container and all nested objects, creating completely independent data structures.",
                "evaluation_criteria": ["Reference vs value", "Nested mutation hazards", "Standard library copy module"]
            }
        ],
        "Advanced": [
            {
                "question": "Explain how Python descriptors work under the hood and how properties, methods, and class methods are implemented using them.",
                "expected_points": [
                    "Descriptors implement __get__, __set__, or __delete__ methods",
                    "Data descriptors vs non-data descriptors and lookup precedence",
                    "@property implements __get__ and __set__",
                    "Functions are non-data descriptors binding methods to instances"
                ],
                "ideal_answer": "A descriptor is any Python object that defines __get__, __set__, or __delete__ methods to customize attribute access. In attribute lookup, data descriptors take precedence over instance dictionaries, while non-data descriptors yield to them. Python properties are data descriptors, and standard functions are non-data descriptors whose __get__ method binds the function to an instance as a method.",
                "evaluation_criteria": ["Lookup order", "Data vs non-data descriptors", "Property implementation"]
            },
            {
                "question": "How does Python's asyncio event loop, coroutines, and tasks work for building high-concurrency systems?",
                "expected_points": [
                    "Single-threaded cooperative multitasking event loop",
                    "Coroutines defined with async def and paused with await",
                    "Tasks wrap coroutines as asyncio.Future objects for concurrent scheduling",
                    "Non-blocking I/O using OS primitives like select/epoll"
                ],
                "ideal_answer": "Asyncio uses a single-threaded event loop based on cooperative multitasking. Coroutines defined with 'async def' pause execution upon encountering 'await' on non-blocking I/O, yielding control back to the event loop. The loop uses OS-level multiplexing like epoll to poll file descriptors and resume coroutines wrapped as Tasks once data is ready, achieving thousands of concurrent connections with minimal overhead.",
                "evaluation_criteria": ["Cooperative multitasking", "Event loop mechanics", "Non-blocking I/O"]
            },
            {
                "question": "Explain Python's Method Resolution Order (MRO) with multiple inheritance and C3 linearization.",
                "expected_points": [
                    "MRO determines the order in which base classes are searched for attributes/methods",
                    "Python uses the C3 Linearization algorithm",
                    "Rules: subclass before superclass, monotonicity, preserving local precedence",
                    "Proper usage of super() for cooperative multiple inheritance"
                ],
                "ideal_answer": "Method Resolution Order (MRO) defines the exact sequence Python follows when resolving methods in inheritance hierarchies. Since Python 2.3, it uses the C3 Linearization algorithm to ensure monotonicity and respect local precedence order so children precede parents. Using super() cooperatively guarantees every class in the MRO is invoked exactly once.",
                "evaluation_criteria": ["C3 Linearization", "Monotonicity", "super() mechanics"]
            }
        ]
    },

    "django": {
        "Beginner": [
            {
                "question": "Explain Django's MVT (Model-View-Template) architectural pattern and how it differs from traditional MVC.",
                "expected_points": [
                    "Model handles data and business logic via ORM",
                    "View handles HTTP request logic and returns HTTP response (equivalent to Controller in MVC)",
                    "Template handles user interface and HTML rendering (equivalent to View in MVC)",
                    "Django itself acts as the Controller routing URLs to views"
                ],
                "ideal_answer": "Django follows the Model-View-Template (MVT) pattern. The Model defines the database schema and business logic. The Template represents the presentation layer, formatting HTML and dynamic data. The View acts as the processing layer that receives HTTP requests, queries the model, and renders the template. In traditional MVC, Django's View acts as the Controller, while Django itself handles overall framework routing.",
                "evaluation_criteria": ["MVT definition", "Mapping to MVC", "Django as controller"]
            },
            {
                "question": "What are Django migrations and what is the difference between 'makemigrations' and 'migrate'?",
                "expected_points": [
                    "Migrations propagate changes made to models into the database schema",
                    "'makemigrations' packages model changes into new migration files",
                    "'migrate' executes the migration scripts against the active database",
                    "Tracking migration history in django_migrations table"
                ],
                "ideal_answer": "Django migrations are version-controlled Python files that translate model schema definitions into database DDL changes. 'makemigrations' inspects your models, detects changes, and generates new migration files without altering the database. 'migrate' actually executes those migration files against the database, synchronizing tables and recording executed migrations in the django_migrations table.",
                "evaluation_criteria": ["makemigrations vs migrate", "Version control of schema", "django_migrations table"]
            },
            {
                "question": "Explain the role of 'urls.py', views, and templates in processing an incoming HTTP request in Django.",
                "expected_points": [
                    "Request lands on Root URLconf (urls.py) and matches path pattern",
                    "URL dispatcher calls the associated view function or class",
                    "View executes business logic, queries ORM, builds context",
                    "View returns HttpResponse or renders template with context"
                ],
                "ideal_answer": "When an HTTP request reaches Django, the URL dispatcher in urls.py matches the requested URL against registered URL patterns. Once a match is found, Django routes the request object to the designated view. The view executes business logic, interacts with models, populates a context dictionary, and renders an HTML template or returns a JSON HttpResponse.",
                "evaluation_criteria": ["Request-response lifecycle", "URL routing", "Context passing"]
            }
        ],
        "Intermediate": [
            {
                "question": "Explain the difference between 'select_related' and 'prefetch_related' in Django ORM and how they solve the N+1 query problem.",
                "expected_points": [
                    "N+1 query problem occurs when accessing related objects in a loop executes individual SQL queries",
                    "'select_related' uses SQL JOIN (best for ForeignKey and OneToOneField)",
                    "'prefetch_related' performs separate queries and joins in Python (best for ManyToManyField and reverse ForeignKey)",
                    "Performance impact and memory trade-offs"
                ],
                "ideal_answer": "Both methods solve the N+1 query problem where accessing foreign key relationships inside loops causes excessive database round-trips. 'select_related' performs an SQL JOIN in a single query, making it optimal for single-valued relationships like ForeignKey and OneToOneField. 'prefetch_related' issues two queries and matches relationships in Python memory, which is necessary for multi-valued relationships like ManyToManyField.",
                "evaluation_criteria": ["N+1 problem understanding", "SQL JOIN vs separate queries", "Relationship type mapping"]
            },
            {
                "question": "How does Django's middleware architecture work, and how do you write custom middleware?",
                "expected_points": [
                    "Middleware is a hooks framework executed on request and response processing",
                    "Middleware executes in top-down order on request, bottom-up on response",
                    "Structure: __init__(get_response) and __call__(request)",
                    "Common built-in middleware: Authentication, Security, CsrfViewMiddleware"
                ],
                "ideal_answer": "Django middleware is a lightweight plugin system of hooks that intercept every incoming request and outgoing response globally. When a request arrives, middleware executes in the order listed in MIDDLEWARE; on response, it executes in reverse order. To write custom middleware, you create a callable class that accepts get_response in its __init__, and processes the request before and after calling self.get_response(request).",
                "evaluation_criteria": ["Execution order", "Request-response cycle", "Callable class structure"]
            },
            {
                "question": "How does Django protect applications against common web vulnerabilities like CSRF, SQL Injection, and XSS?",
                "expected_points": [
                    "CSRF: CsrfViewMiddleware, hidden tokens in POST forms, SameSite cookies",
                    "SQL Injection: Parameterized queries in Django ORM",
                    "XSS: Automatic HTML escaping in Django template system",
                    "Clickjacking: X-Frame-Options middleware"
                ],
                "ideal_answer": "Django has security built-in by default. For CSRF, it uses CsrfViewMiddleware and synchronized tokens checked on state-changing POST requests. For SQL Injection, Django ORM automatically parameterizes SQL queries, ensuring user inputs are treated as data rather than executable SQL. For XSS, Django's template engine automatically escapes special characters unless explicitly marked as safe.",
                "evaluation_criteria": ["CSRF tokens", "Parameterized ORM queries", "Auto-escaping templates"]
            }
        ],
        "Advanced": [
            {
                "question": "How do you optimize database query performance for large datasets in Django using indexes, bulk operations, and caching?",
                "expected_points": [
                    "Database indexing (db_index=True, Meta.indexes compound/functional)",
                    "Bulk operations: bulk_create, bulk_update, in_bulk to avoid loop saves",
                    "QuerySet optimizations: only(), defer(), iterator(), values_list()",
                    "Caching QuerySets with Redis or Memcached"
                ],
                "ideal_answer": "Optimizing Django database performance requires multiple coordinated strategies. First, add compound and B-tree indexes to frequently filtered and joined fields. Second, replace iterative saves with bulk_create and bulk_update to minimize round-trips. Third, use only() and defer() to fetch only required columns, iterator() for streaming large datasets without caching them in RAM, and store hot queries in a Redis cache layer.",
                "evaluation_criteria": ["Indexing strategy", "Bulk operations", "QuerySet memory management"]
            },
            {
                "question": "How do you handle database race conditions and ensure data consistency in Django using transactions and locking?",
                "expected_points": [
                    "transaction.atomic() to ensure ACID compliance",
                    "Pessimistic locking with select_for_update() to lock rows",
                    "Optimistic locking using versioning numbers or F() expressions",
                    "Database deadlocks avoidance strategies"
                ],
                "ideal_answer": "To prevent race conditions like concurrent inventory decrements, wrap critical logic in 'with transaction.atomic()'. Use pessimistic locking via select_for_update() to lock selected rows in the database until the transaction commits, preventing other workers from modifying them. Alternatively, for high-throughput low-contention scenarios, use Django F() expressions or optimistic locking with version fields to apply atomic database-level arithmetic.",
                "evaluation_criteria": ["transaction.atomic()", "select_for_update()", "F() expressions"]
            }
        ]
    },

    "javascript": {
        "Beginner": [
            {
                "question": "Explain the difference between 'var', 'let', and 'const' in JavaScript.",
                "expected_points": [
                    "'var' is function-scoped and hoisted with undefined initialization",
                    "'let' and 'const' are block-scoped ({ }) and hoisted in Temporal Dead Zone (TDZ)",
                    "'const' cannot be reassigned (though objects remain mutable)",
                    "Modern best practice: prefer const, use let when reassigning, avoid var"
                ],
                "ideal_answer": "'var' is function-scoped and hoisted with an initial value of undefined, allowing it to be redeclared and accessed before declaration. In contrast, 'let' and 'const' are block-scoped and reside in the Temporal Dead Zone until their definition is reached. 'const' prevents variable reassignment, although properties of objects assigned to const can still be modified.",
                "evaluation_criteria": ["Scope differences", "Hoisting and TDZ", "Reassignment rules"]
            },
            {
                "question": "What is the difference between '==' and '===' in JavaScript?",
                "expected_points": [
                    "'==' performs type coercion before comparison (abstract equality)",
                    "'===' checks both value and type without coercion (strict equality)",
                    "Examples of unexpected coercion with '==' (e.g. 0 == '', null == undefined)",
                    "Best practice: always use '==='"
                ],
                "ideal_answer": "'==' is the loose equality operator that performs implicit type coercion, converting operands to a common type before comparing them. '===' is the strict equality operator that compares both the value and the type without coercion. For example, '5' == 5 evaluates to true, but '5' === 5 evaluates to false. Developers should always default to '===' to prevent subtle bugs.",
                "evaluation_criteria": ["Type coercion", "Strict equality", "Predictable coding practice"]
            },
            {
                "question": "Explain how Promises work in JavaScript and the difference between .then() and async/await.",
                "expected_points": [
                    "Promise states: Pending, Fulfilled, Rejected",
                    ".then() and .catch() for chaining callbacks",
                    "async/await is syntactic sugar over Promises enabling synchronous-looking code",
                    "Error handling with try/catch vs .catch()"
                ],
                "ideal_answer": "A Promise represents the eventual completion or failure of an asynchronous operation, existing in one of three states: pending, fulfilled, or rejected. While .then() chains callback handlers asynchronously, async/await provides clean syntactic sugar built on top of Promises, allowing developers to write asynchronous code that reads sequentially and handles errors with standard try/catch blocks.",
                "evaluation_criteria": ["Promise states", "Async/await mechanics", "Error handling"]
            }
        ],
        "Intermediate": [
            {
                "question": "Explain closures in JavaScript and provide a practical real-world use case.",
                "expected_points": [
                    "A closure is a function bundled together with references to its surrounding lexical environment",
                    "Inner function retains access to outer variables even after outer function has returned",
                    "Use case: data privacy / private variables",
                    "Use case: function factories or currying"
                ],
                "ideal_answer": "A closure is created whenever a function is defined, giving the inner function access to its outer lexical scope even after the outer function has finished executing. A classic use case is data privacy, where you encapsulate private state within an outer function and return public methods that manipulate that state without exposing it directly to the global scope.",
                "evaluation_criteria": ["Lexical scope retention", "Data privacy example", "Function lifecycle"]
            },
            {
                "question": "Explain the JavaScript Event Loop, call stack, microtask queue, and macrotask queue.",
                "expected_points": [
                    "Call stack executes synchronous code",
                    "Web APIs / Node APIs handle async operations in the background",
                    "Microtask queue (Promises, queueMicrotask) has higher priority than macrotask queue",
                    "Macrotask queue (setTimeout, setInterval, I/O) executes after microtasks drain"
                ],
                "ideal_answer": "JavaScript is single-threaded and executes synchronous code on the Call Stack. When asynchronous operations finish in browser/Node APIs, their callbacks enter queues. The Event Loop monitors the call stack: once empty, it processes ALL callbacks in the Microtask Queue (such as Promise resolutions) before picking the next callback from the Macrotask Queue (such as setTimeout or I/O).",
                "evaluation_criteria": ["Call stack", "Microtask priority over macrotasks", "Event loop synchronization"]
            }
        ],
        "Advanced": [
            {
                "question": "How do you identify, profile, and fix memory leaks in large single-page JavaScript applications?",
                "expected_points": [
                    "Common leak causes: uncleared setInterval, detached DOM elements, global variables, closures holding large scopes",
                    "Profiling tools: Chrome DevTools Memory tab, Heap Snapshots, Allocation Timelines",
                    "Techniques: comparing heap snapshots to find retained objects",
                    "Preventative practices: cleaning up listeners and component unmount hooks"
                ],
                "ideal_answer": "Memory leaks in JavaScript typically occur from uncleared timers, abandoned event listeners, closures retaining large objects, or detached DOM trees referenced in memory. To diagnose them, use Chrome DevTools Memory profiler to capture and compare heap snapshots before and after a user workflow. Look for growing retainer trees, ensure event listeners are removed on component unmount, and set unused references to null.",
                "evaluation_criteria": ["Leak causes", "Heap snapshots profiling", "Proper cleanup patterns"]
            }
        ]
    },

    "react": {
        "Beginner": [
            {
                "question": "What is the Virtual DOM in React and how does reconciliation work?",
                "expected_points": [
                    "Virtual DOM is an in-memory representation of real DOM elements",
                    "State or prop changes generate a new Virtual DOM tree",
                    "Diffing algorithm (reconciliation) compares previous and new trees",
                    "Batch updates applied to real DOM to minimize expensive reflows"
                ],
                "ideal_answer": "The Virtual DOM is a lightweight JavaScript object representation of the actual DOM kept in memory. When a component's state or props change, React creates a new Virtual DOM tree and runs a diffing algorithm called reconciliation to compare it with the previous tree. It calculates the minimum required changes and batches those updates to the real DOM, avoiding expensive browser layout and reflow operations.",
                "evaluation_criteria": ["Virtual DOM concept", "Diffing algorithm", "Batching real DOM updates"]
            },
            {
                "question": "Explain the difference between state and props in React.",
                "expected_points": [
                    "Props are passed from parent to child and are read-only (immutable)",
                    "State is managed internally within a component and is mutable via setter functions",
                    "Unidirectional data flow in React",
                    "State changes trigger component re-renders"
                ],
                "ideal_answer": "Props are input arguments passed from a parent component down to a child component; they are read-only and immutable to the receiving component. State is internal data managed and owned by the component itself, which can change over time via state setter functions. When state updates, React re-renders the component and its children to reflect the new data.",
                "evaluation_criteria": ["Ownership and mutability", "Unidirectional data flow", "Re-render triggers"]
            }
        ],
        "Intermediate": [
            {
                "question": "Explain the useEffect hook in React, including its dependency array and cleanup functions.",
                "expected_points": [
                    "Used for side effects (API calls, subscriptions, DOM manipulation)",
                    "No dependency array runs on every render; empty [] runs only on mount",
                    "Dependencies array [a, b] runs when specified values change",
                    "Cleanup function runs before unmount or before the effect re-runs"
                ],
                "ideal_answer": "The useEffect hook lets you perform side effects in functional components, such as data fetching, subscriptions, or manual DOM updates. Passing no dependency array runs the effect after every render; an empty array [] runs it once when the component mounts; and listing specific dependencies runs it only when those values change. Returning a cleanup function ensures event listeners and timers are cleanly removed before unmount or subsequent runs.",
                "evaluation_criteria": ["Dependency array nuances", "Cleanup function necessity", "Side effect lifecycle"]
            },
            {
                "question": "What is the difference between useMemo and useCallback, and when should you use them?",
                "expected_points": [
                    "useMemo memoizes the result of a calculation",
                    "useCallback memoizes a function definition",
                    "Used to prevent unnecessary re-computations or child re-renders with React.memo",
                    "Premature optimization caveat: overhead of hook vs cheap operations"
                ],
                "ideal_answer": "Both hooks optimize rendering performance by memoizing values across renders. useMemo caches the computed result of an expensive calculation and only recalculates it when its dependencies change. useCallback caches the function definition itself, which is useful when passing callbacks to memoized child components to prevent breaking referential equality. They should only be used when measurable performance benefits exist.",
                "evaluation_criteria": ["Memoized value vs function", "Referential equality", "Avoid premature optimization"]
            }
        ],
        "Advanced": [
            {
                "question": "Explain React 18 Concurrent Features, automatic batching, and how 'useTransition' improves perceived performance.",
                "expected_points": [
                    "Concurrent React allows rendering to be interrupted and prioritized",
                    "Automatic batching groups state updates inside promises, timeouts, and handlers into a single render",
                    "useTransition marks non-urgent state updates to keep UI responsive",
                    "Suspense for asynchronous code and data streaming"
                ],
                "ideal_answer": "React 18 introduces concurrent rendering, allowing React to prepare multiple versions of the UI in memory, pause rendering, and prioritize urgent user interactions over non-urgent updates. Automatic batching now groups state changes across promises and setTimeout into single re-renders. The useTransition hook allows developers to mark heavy state changes as non-urgent transitions, keeping the user input interface responsive while background rendering takes place.",
                "evaluation_criteria": ["Concurrent rendering", "Urgent vs non-urgent updates", "useTransition usage"]
            }
        ]
    },

    "sql": {
        "Beginner": [
            {
                "question": "Explain the difference between INNER JOIN, LEFT JOIN, RIGHT JOIN, and FULL OUTER JOIN.",
                "expected_points": [
                    "INNER JOIN returns matching rows from both tables",
                    "LEFT JOIN returns all rows from the left table and matched rows from the right",
                    "RIGHT JOIN returns all rows from the right table and matched rows from the left",
                    "FULL OUTER JOIN returns rows when there is a match in either table, filling NULLs"
                ],
                "ideal_answer": "An INNER JOIN returns only records that have matching keys in both tables. A LEFT JOIN returns all rows from the left table along with matched rows from the right table, populating NULL for missing right-side values. A RIGHT JOIN does the reverse, returning all rows from the right table. A FULL OUTER JOIN returns all records from both tables, filling with NULL wherever a relationship does not match.",
                "evaluation_criteria": ["Join behavior", "NULL handling", "Use cases"]
            },
            {
                "question": "What is the difference between the WHERE and HAVING clauses in SQL?",
                "expected_points": [
                    "WHERE filters individual rows before grouping occurs",
                    "HAVING filters aggregated groups after GROUP BY",
                    "WHERE cannot use aggregate functions (e.g. SUM, COUNT)",
                    "HAVING is designed specifically to work with aggregate conditions"
                ],
                "ideal_answer": "The WHERE clause filters individual rows before any grouping or aggregation takes place, and it cannot evaluate aggregate functions like COUNT() or AVG(). The HAVING clause filters grouped records after the GROUP BY operation has aggregated the rows, allowing conditions based on aggregate calculations.",
                "evaluation_criteria": ["Pre vs post aggregation", "Aggregate functions compatibility", "Query execution order"]
            }
        ],
        "Intermediate": [
            {
                "question": "Explain the ACID properties of relational database transactions with concrete examples.",
                "expected_points": [
                    "Atomicity: all operations succeed or the entire transaction is rolled back",
                    "Consistency: transactions move the database from one valid state to another satisfying constraints",
                    "Isolation: concurrent transactions execute without interfering with one another",
                    "Durability: committed transactions survive system crashes and power failures"
                ],
                "ideal_answer": "ACID ensures reliable database transactions. Atomicity guarantees all-or-nothing execution, meaning if a bank transfer debits account A but fails to credit account B, the entire transaction rolls back. Consistency ensures schema rules and foreign keys are never violated. Isolation prevents concurrent transactions from seeing uncommitted dirty reads. Durability guarantees that once committed, data is written to persistent storage and survives crashes.",
                "evaluation_criteria": ["All four principles defined", "Practical banking example", "Database reliability guarantee"]
            },
            {
                "question": "How do B-Tree indexes work in databases, and what are the trade-offs of adding too many indexes?",
                "expected_points": [
                    "B-Trees maintain sorted balance for fast O(log N) lookups, range scans, and sorting",
                    "Speed up SELECT queries significantly",
                    "Slow down INSERT, UPDATE, and DELETE queries because indexes must be rebalanced",
                    "Consume substantial additional disk and memory space"
                ],
                "ideal_answer": "B-Tree indexes organize table keys in a balanced tree structure that allows the database engine to locate records in O(log N) time rather than doing full table scans. While indexes dramatically accelerate SELECT queries and range searches, adding too many creates overhead: every INSERT, UPDATE, and DELETE must update and rebalance the tree, and indexes consume significant memory and disk storage.",
                "evaluation_criteria": ["O(log N) complexity", "Read vs write trade-off", "Storage implications"]
            }
        ],
        "Advanced": [
            {
                "question": "Explain database isolation levels and the concurrency anomalies they prevent (Dirty Read, Non-Repeatable Read, Phantom Read).",
                "expected_points": [
                    "Read Uncommitted: allows dirty reads",
                    "Read Committed: prevents dirty reads",
                    "Repeatable Read: prevents dirty and non-repeatable reads",
                    "Serializable: strictest level, prevents phantom reads by locking or serialization",
                    "Performance trade-off between higher isolation and concurrency throughput"
                ],
                "ideal_answer": "SQL standard isolation levels balance concurrency throughput against data consistency anomalies. Read Uncommitted allows transactions to read uncommitted changes (dirty reads). Read Committed ensures only committed data is visible, but a row read twice may change (non-repeatable read). Repeatable Read locks read rows to guarantee consistent reads throughout the transaction. Serializable is the highest level, preventing phantom rows where new inserts appear in range queries, typically using MVCC or range locks.",
                "evaluation_criteria": ["Isolation levels hierarchy", "Three anomalies explained", "MVCC and lock trade-offs"]
            }
        ]
    }
}

# =====================================================================
# DYNAMIC QUESTION GENERATION LOGIC
# =====================================================================

def generate_local_interview_questions(
    interview_type: str,
    domain: str,
    technology: str,
    difficulty: str,
    num_questions: int,
    language: str = "English"
) -> List[Dict[str, Any]]:
    """
    Generates structured interview questions from the curated bank without calling Gemini.
    Guarantees exact count, expected points, ideal answers, and evaluation criteria.
    """
    clean_type = (interview_type or "Technical").lower()
    clean_tech = (technology or "General").lower().strip()
    clean_diff = difficulty.capitalize() if difficulty in ["Beginner", "Intermediate", "Advanced"] else "Intermediate"
    target_count = max(1, min(int(num_questions or 5), 20))

    pool: List[Dict[str, Any]] = []

    # 1. Match Interview Type
    if "hr" in clean_type:
        pool = list(HR_QUESTIONS)
    elif "behavioral" in clean_type:
        pool = list(BEHAVIORAL_QUESTIONS) + list(HR_QUESTIONS)
    elif "mixed" in clean_type:
        pool = list(HR_QUESTIONS[:3]) + list(BEHAVIORAL_QUESTIONS[:2])
        # Find matching tech questions to mix in
        tech_key = _find_matching_tech_key(clean_tech)
        if tech_key and tech_key in TOPIC_QUESTIONS:
            tech_pool = TOPIC_QUESTIONS[tech_key].get(clean_diff, [])
            pool = pool[:target_count // 2] + tech_pool[:target_count - (target_count // 2)]
    else:
        # Technical Interview: Find topic match
        tech_key = _find_matching_tech_key(clean_tech)
        if tech_key and tech_key in TOPIC_QUESTIONS:
            diff_dict = TOPIC_QUESTIONS[tech_key]
            # Primary difficulty pool
            primary = diff_dict.get(clean_diff, [])
            pool.extend(primary)
            # If not enough, pull from other difficulties
            for d in ["Intermediate", "Beginner", "Advanced"]:
                if d != clean_diff:
                    for q in diff_dict.get(d, []):
                        if q not in pool:
                            pool.append(q)

    # 2. If pool is still smaller than target_count, synthesize high-quality questions for this technology
    if len(pool) < target_count:
        synthesized = _synthesize_technology_questions(technology or domain, clean_diff, target_count - len(pool))
        pool.extend(synthesized)

    # 3. Take exactly target_count questions
    selected = pool[:target_count]

    # 4. Standardize output format
    formatted_questions = []
    for item in selected:
        formatted_questions.append({
            "question": item.get("question", f"Explain the core architectural principles of {technology}."),
            "interview_type": interview_type,
            "domain": domain,
            "topic": technology,
            "difficulty": item.get("difficulty", clean_diff),
            "question_type": item.get("question_type", "Conceptual"),
            "expected_points": item.get("expected_points", [
                "Clear conceptual definition",
                "Practical implementation details",
                "Best practices and common pitfalls"
            ]),
            "ideal_answer": item.get("ideal_answer", f"A strong answer clearly defines the concept in {technology}, explains practical application, and highlights performance trade-offs."),
            "evaluation_criteria": item.get("evaluation_criteria", [
                "Technical accuracy",
                "Depth of explanation",
                "Clarity and communication"
            ])
        })

    return formatted_questions


def _find_matching_tech_key(clean_tech: str) -> str:
    """Finds best matching category key in TOPIC_QUESTIONS."""
    if any(k in clean_tech for k in ["python", "py", "flask", "fastapi"]):
        return "python"
    if any(k in clean_tech for k in ["django"]):
        return "django"
    if any(k in clean_tech for k in ["javascript", "js", "typescript", "ts", "node"]):
        return "javascript"
    if any(k in clean_tech for k in ["react", "frontend", "next.js"]):
        return "react"
    if any(k in clean_tech for k in ["sql", "database", "postgres", "mysql", "sqlite", "mongodb"]):
        return "sql"
    return "python"


def _synthesize_technology_questions(tech_name: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """Synthesizes structured questions for any technology or domain."""
    templates = [
        {
            "template": "What are the core architectural principles and design patterns of {tech}?",
            "expected_points": [
                f"Fundamental components and design philosophy of {tech}",
                "Typical architectural patterns (e.g. modular, layered, event-driven)",
                "How {tech} handles separation of concerns"
            ],
            "ideal_answer": f"{tech} is architected around modular components, clear separation of concerns, and robust error boundaries to enable high scalability and maintainability."
        },
        {
            "template": "How does {tech} manage performance, concurrency, and memory under high load?",
            "expected_points": [
                f"Resource allocation and memory management in {tech}",
                "Concurrency or threading models supported",
                "Caching, connection pooling, or optimization strategies"
            ],
            "ideal_answer": f"Performance in {tech} relies on efficient resource management, minimizing memory leaks, and applying caching and non-blocking I/O where appropriate."
        },
        {
            "template": "What are the most common pitfalls or anti-patterns when building production systems with {tech}?",
            "expected_points": [
                f"Common developer mistakes when implementing {tech}",
                "Security vulnerabilities or misconfigurations",
                "How to mitigate these pitfalls with automated tests and monitoring"
            ],
            "ideal_answer": f"Common pitfalls with {tech} include improper error handling, neglecting boundary conditions, and unoptimized queries, which should be caught through CI/CD test automation."
        },
        {
            "template": "How do you test, debug, and monitor an enterprise application built with {tech}?",
            "expected_points": [
                "Unit testing frameworks and integration testing methodologies",
                "Debugging tools and profiling techniques",
                "Logging, distributed tracing, and APM metrics"
            ],
            "ideal_answer": f"Robust testing in {tech} combines isolated unit tests, end-to-end integration tests, structured JSON logging, and APM metrics to diagnose latency bottlenecks."
        },
        {
            "template": "Describe a real-world scenario where you had to refactor or scale a feature in {tech}.",
            "expected_points": [
                "Context of the bottleneck or tech debt",
                f"Technical decisions made using {tech} tools",
                "Measurable outcome in performance, readability, or reliability"
            ],
            "ideal_answer": f"In a high-traffic service, we profiled {tech} operations, eliminated redundant data conversions, and improved throughput by over 50% with zero downtime."
        }
    ]

    results = []
    for i in range(count):
        tmpl = templates[i % len(templates)]
        results.append({
            "question": tmpl["template"].format(tech=tech_name),
            "difficulty": difficulty,
            "question_type": "Practical & Conceptual",
            "expected_points": tmpl["expected_points"],
            "ideal_answer": tmpl["ideal_answer"],
            "evaluation_criteria": ["Technical accuracy", "Practical problem-solving", "Depth of experience"]
        })
    return results

# Global Rules for Optimum Application Performance: PhotoPortfolio (Windsurf Project)

## 1. Code Quality & Best Practices
- Write modular, reusable, and well-documented code.
- Follow framework-specific best practices (React, Nuxt, Flask, etc.).
- Use environment variables for configuration; never hardcode secrets.
- Enforce code linting and formatting with tools like ESLint, Prettier, or Black.

## 2. Frontend Performance
- Optimize images (compression, responsive sizes, lazy loading).
- Minimize and bundle JS/CSS assets; use code splitting.
- Use a CDN for static assets when possible.
- Implement caching strategies for static files.
- Avoid blocking the main thread; use async loading for heavy resources.

## 3. Backend Performance
- Use efficient database queries and proper indexing.
- Cache frequent queries and API responses where appropriate.
- Use asynchronous processing for heavy or long-running tasks.
- Limit payload sizes and paginate large responses.

## 4. Security
- Use HTTPS everywhere; never transmit sensitive data over HTTP.
- Sanitize all user inputs and validate on both client and server.
- Store passwords securely (hashed and salted).
- Use role-based access control and least-privilege principles.

## 5. Resource Management
- Monitor CPU, memory, and storage usage; set up alerts for anomalies.
- Use auto-scaling or serverless options to handle load spikes.
- Regularly review and optimize cloud resource usage to control costs.

## 6. Deployment & CI/CD
- Automate builds, tests, and deployments using CI/CD pipelines.
- Run automated tests on every pull request; block merges on test failures.
- Use blue/green or rolling deployments to minimize downtime.
- Maintain versioned backups of production data and configurations.

## 7. Monitoring & Logging
- Implement centralized logging and error tracking.
- Set up real-time monitoring and alerting for uptime, errors, and performance.
- Regularly review logs and metrics to identify and resolve bottlenecks.

## 8. Documentation
- Maintain up-to-date documentation for setup, deployment, and usage.
- Document all APIs, environment variables, and configuration options.
- Provide onboarding guides for new developers and users.

---

_Adherence to these global rules ensures high performance, security, and maintainability for the PhotoPortfolio application on Windsurf or any cloud platform._

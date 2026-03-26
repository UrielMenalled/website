# The Agroecology Lab - GitHub Pages Website

A multi-page website for The Agroecology Lab at Montana State University, designed for deployment on GitHub Pages. The GitHub actions associated with this repository should update the publications and code using my Semantic Scholars and GitHub accounts, respectively. In my opinion, this is the stand-out benefit of this website. If you want to reap these benefits, you will need to create an account for both services, make updates to the variables (in repo settings) and scripts.

Some of the important files in this repo include

```
docs/
├── index.html          # Homepage
├── team.html           # Meet the Team
├── research.html       # Research Areas
├── teaching.html       # Teaching Experience
├── publications.html   # Publications List
├── join.html           # Join Us / Prospective Students
└── styles.css          # Shared stylesheet
```

## Some notes for people interested in using this code

### Updating Colors

Edit the CSS variables in `public/styles.css`:

```css
:root {
  --primary-green: #2c5f2d;    /* Main brand color */
  --accent-orange: #d97a34;     /* Accent color */
  --text-dark: #2d2d2d;         /* Body text */
  --text-light: #666;           /* Secondary text */
  --background-light: #f8f8f8;  /* Background sections */
}
```

### Adding New Pages

1. Create a new HTML file in the `public` folder
2. Copy the header and footer from an existing page
3. Add a link to the new page in the navigation menu of all pages

### Browser Support (at the moment of project initialization)

- Chrome
- Firefox
- Safari
- Edge

## License

People are free to use this repository as a template for their own website. However, all content on this website belongs to Uriel Menalled and the Agroecology Lab at Montana State University.

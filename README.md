# The Agroecology Lab - GitHub Pages Website

A multi-page website for The Agroecology Lab at Montana State University, designed for deployment on GitHub Pages. **The GitHub actions associated with this repository should update the publications and code automatically every 30 days using my Semantic Scholars and GitHub accounts, respectively.** In my opinion, this is the stand-out benefit of this website. If you want to reap these benefits, you will need to create an account for both services, make updates to the variables (in repo settings) and scripts.

Some of the important files in this repo include

```
.github/                    # The automation folder
├── workflows/                # Folder with instructions
└── CODEOWNERS                # File listing who can approve pull requests
docs/                       # The website folder
├── images/                   # Folder with all images
├── videos/                   # Folder with all videos
├── index.html                # Homepage
├── team.html                 # Meet the Team
├── research.html             # Research Areas
├── teaching.html             # Teaching Experience
├── publications.html         # Publications List
├── join.html                 # Join Us / Prospective Students
└── styles.css                # Website formatting/styles
scripts/                    # The webscraping folder
├── update-repos.js           # GitHub account scraping
└── update_publications.py    # SemanticScholars account publication scraping
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

1. Create a new HTML file in the `docs` folder
2. Copy the header and footer from an existing page
3. Add a link to the new page in the navigation menu of all pages

### Browser Support (at the moment of project initialization)

- Chrome
- Firefox
- Safari
- Edge

## Long-term support
Irregularly, I will back up this repository on Zenodo. Only use the Zenodo files if this repository are down (you won't be able to access the the following link if my repository is down, but alas, you can probably look my name up in Zenodo so something): [![DOI](https://zenodo.org/badge/latestdoi/UrielMenalled/lab-website.svg)](https://zenodo.org/badge/latestdoi/UrielMenalled/lab-website)

## License

People are free to use this repository as a template for their own website. However, all content on this website belongs to Uriel Menalled and the Agroecology Lab at Montana State University.

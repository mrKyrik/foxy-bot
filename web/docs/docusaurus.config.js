// @ts-check
import {themes as prismThemes} from 'prism-react-renderer';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Kumiho Bot',
  tagline: 'Kapsamlı Discord Bot Dokümantasyonu',
  favicon: 'img/favicon.ico',

  url: 'https://docs-foxy.duckdns.org',
  baseUrl: '/',

  organizationName: 'mrKyrik',
  projectName: 'kumiho-bot',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'tr',
    locales: ['tr'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          routeBasePath: '/', // Serve the docs at the site's root
        },
        blog: false, // Disable blog
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Kumiho Bot',
        logo: {
          alt: 'Kumiho Bot Logo',
          src: 'img/logo.svg', // Will need to replace this later
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Dokümantasyon',
          },
          {
            href: 'https://admin-foxy.duckdns.org',
            label: 'Admin Panel',
            position: 'right',
          },
          {
            href: 'https://github.com/mrKyrik/foxy-bot',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark', // We'll override this in custom.css for Microsoft look
        links: [
          {
            title: 'Bağlantılar',
            items: [
              {
                label: 'Dokümantasyon',
                to: '/',
              },
              {
                label: 'Admin Panel',
                href: 'https://admin-foxy.duckdns.org',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Kumiho Bot. Docusaurus ile oluşturuldu.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;

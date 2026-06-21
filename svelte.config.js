import adapter from '@sveltejs/adapter-auto';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	compilerOptions: {
		runes: true
	},
	kit: {
		adapter: adapter(),
		files: {
			routes: 'frontend/routes',
			lib: 'frontend/lib',
			appTemplate: 'frontend/app.html'
		},
		alias: {
			$components: 'frontend/components',
			$stores: 'frontend/stores'
		}
	}
};

export default config;

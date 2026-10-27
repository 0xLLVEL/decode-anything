<?php

namespace SpondonIt\Service;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * SpondonItServiceProvider.php
 */

class SpondonItServiceProvider extends Illuminate\Support\ServiceProvider {
    public function register(): void {
        $this->mergeConfigFrom(__DIR__ . '/../config/spondonit.php', 'spondonit');
        $this->app->bindIf('SpondonIt\\Service\\Contracts\\AppLifecycleInterface', 'SpondonIt\\Service\\Support\\NullAppLifecycle');
        Illuminate\Support\Facades\App::macro('isInstalled', function () {
            return (bool) (Illuminate\Support\Facades\Storage::exists('.app_installed') && Illuminate\Support\Facades\Storage::get('.app_installed'));
        });
    }

    public function boot(): void {
        $kernel = $this->app->make('Illuminate\\Contracts\\Http\\Kernel');
        $kernel->pushMiddleware('SpondonIt\\Service\\Middleware\\InstallationGuardMiddleware');
        $router = $this->app['router'];
        $router->pushMiddlewareToGroup('web', 'SpondonIt\\Service\\Middleware\\ServiceMiddleware');
        $this->loadRoutesFrom(__DIR__ . '/../routes/web.php');
        $this->loadRoutesFrom(__DIR__ . '/../routes/api.php');
        $this->loadTranslationsFrom(__DIR__ . '/../resources/lang', 'service');
        if (is_dir(resource_path('/views/vendors/service'))) {
            $this->loadViewsFrom(resource_path('/views/vendors/service'), 'service');
        } else {
            $this->loadViewsFrom(__DIR__ . '/../resources/views', 'service');
        }
        $this->publishes([
            __DIR__ . '/../public' => public_path('vendor/spondonit'),
            __DIR__ . '/../resources/views' => resource_path('views/vendors/service'),
        ], 'spondonit');
        $this->commands(['SpondonIt\\Service\\Console\\Commands\\MigrateStatusCommand']);
    }
}

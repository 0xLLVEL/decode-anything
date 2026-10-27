<?php

namespace SpondonIt\SchoolService;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * SpondonItSchoolServiceProvider.php
 */

class SpondonItSchoolServiceProvider extends Illuminate\Support\ServiceProvider {
    public function register() {
        $this->app->bind('SpondonIt\\Service\\Contracts\\AppInstallerInterface', 'SpondonIt\\SchoolService\\Installers\\SchoolInstaller');
        $this->app->bind('SpondonIt\\Service\\Contracts\\AppInitializerInterface', 'SpondonIt\\SchoolService\\Initializers\\SchoolInitializer');
        $this->app->bind('SpondonIt\\Service\\Contracts\\AppLifecycleInterface', 'SpondonIt\\SchoolService\\Lifecycle\\SchoolLifecycle');
        $this->mergeConfigFrom(__DIR__ . '/../config/school.php', 'school');
        $prerequisites = (require __DIR__ . '/../config/prerequisites.php');
        config([
            'spondonit.pre_requisite' => array_merge(config('spondonit.pre_requisite', []), []),
            'spondonit.branding.asset_path' => 'public/vendor/spondonit',
            'spondonit.branding.welcome_title' => 'Welcome To Spondonit',
            'spondonit.branding.welcome_description' => 'Thank you for choosing Infix School for online school management. Please follow the steps to complete Infix School installation!',
            'spondonit.branding.admin_setup_title' => 'Admin Setup',
            'spondonit.branding.done_msg' => 'Installation done. You can now login.',
            'spondonit.branding.with_demo_data' => 'Install With Demo Data',
            'spondonit.branding.min_password_chars' => 'Minimum 8 characters',
            'spondonit.branding.same_as_password' => 'Same as Password',
            'spondonit.features.modules' => true,
            'spondonit.module_manager_model' => 'App\\Models\\InfixModuleManager',
            'spondonit.module_manager_table' => 'infix_module_managers',
            'spondonit.saas_module_name' => 'Saas',
            'spondonit.module_status_check_function' => 'moduleStatusCheck',
            'spondonit.settings_model' => 'App\\Models\\SmGeneralSettings',
            'spondonit.module_model' => 'Nwidart\\Modules\\Facades\\Module',
            'spondonit.user_model' => 'App\\User',
            'spondonit.settings_table' => 'sm_general_settings',
            'spondonit.database_file' => 'infix_edu.sql',
            'spondonit.support_multi_connection' => true,
            'spondonit.php_version' => '8.3.0',
            'spondonit.modules' => [
                'Zoom' => '27623128',
                'OnlineExam' => '61700949',
                'ParentRegistration' => '27762693',
                'RazorPay' => '27721206',
                'BBB' => '32314367',
                'Jitsi' => '32973934',
                'Saas' => '30210110',
                'XenditPayment' => '1017070',
                'AppSlider' => '1011010',
                'KhaltiPayment' => '1010909',
                'Raudhahpay' => '1018080',
                'InfixBiometrics' => '10114142',
                'Gmeet' => '42463761',
                'PhonePay' => '10128281',
                'Lms' => '56385810',
                'CcAveune' => '1011212',
                'AiContent' => '50534370',
                'WhatsappSupport' => '50591298',
                'Certificate' => '51017328',
                'InAppLiveClass' => '54845250',
                'MercadoPago' => '37864570',
                'University' => '1011313',
                'ToyyibPay' => '10120201',
                'News' => '20223231',
                'PDF' => '20222221',
                'SaasHr' => '20221211',
                'Forum' => '20224241',
                'CustomMenu' => '20225251',
                'QRCodeAttendance' => '56053599',
                'SslCommerz' => '10127271',
                'CbseExam' => '61209234',
            ],
        ]);
        $this->app->register('App\\Providers\\RepositoryServiceProvider');
        $this->app->singleton('dashboard_background', function () {
            return Illuminate\Support\Facades\DB::table('sm_background_settings')->where('school_id', app('school')->id)->where([['is_default', 1], ['title', 'Dashboard Background']])->first();
        });
        $this->app->singleton('school_general_settings', function () {
            if (app()->bound('school')) {
                return App\Models\SmGeneralSettings::where('school_id', app('school')->id)->first();
            }
            return App\Models\SmGeneralSettings::where('school_id', 1)->first();
        });
        $this->app->singleton('school_menu_permissions', function () {
            $module_ids = getPlanPermissionMenuModuleId();
            return Modules\RolePermission\Entities\InfixModuleInfo::where('parent_id', 0)->with(['children'])->whereIn('id', $module_ids)->get();
        });
        $this->app->singleton('permission', function () {
            $infixRole = Modules\RolePermission\Entities\InfixRole::find(Illuminate\Support\Facades\Auth::user()->role_id);
            $permissionIds = Modules\RolePermission\Entities\AssignPermission::where('role_id', Illuminate\Support\Facades\Auth::user()->role_id)->when($infixRole->is_saas === 0, function ($q) {
                $q->where('school_id', Illuminate\Support\Facades\Auth::user()->school_id);
            })->pluck('permission_id')->toArray();
            $permissions = Modules\RolePermission\Entities\Permission::whereIn('id', $permissionIds)->pluck('route')->toArray();
        });
        $this->app->singleton('saasSettings', function () {
            return Modules\Saas\Entities\SaasSettings::where('saas_status', 0)->pluck('infix_module_id')->toArray();
        });
        $this->app->singleton('sidebar_news', function () {
            return Modules\MenuManage\Entities\Sidebar::get();
        });
    }

    public function boot() {
        Livewire\Livewire::setUpdateRoute(function ($handle) {
            return Illuminate\Support\Facades\Route::post('/custom/livewire/update', $handle);
        });
        Illuminate\Pagination\Paginator::useBootstrapFour();
        Illuminate\Database\Schema\Builder::defaultStringLength(191);
        view()->composer('backEnd.partials.parents_sidebar', function ($view) {
            $data = ['childrens' => App\Models\SmParent::myChildrens()];
            $view->with($data);
        });
        view()->composer('backEnd.partials.menu', function ($view) {
            $notifications = Illuminate\Support\Facades\DB::table('notifications')->where('notifiable_id', auth()->id())->where('read_at', null)->get();
            foreach ($notifications as $notification) {
                $notification->data = json_decode($notification->data);
            }
            $view->with(['notifications_for_chat' => $notifications]);
        });
        view()->composer(['backEnd.master', 'backEnd.partials.menu'], function ($view) {
            $data = ['notifications' => App\Models\SmNotification::notifications()];
            $view->with($data);
        });
        view()->composer(['plugins.tawk_to'], function ($view) {
            $data = [
                'agent' => new Jenssegers\Agent\Agent(),
                'tawk_setting' => App\Models\Plugin::where('name', 'tawk')->where('school_id', app('school')->id)->first(),
            ];
            $view->with($data);
        });
        view()->composer(['backEnd.partials.menu', 'layouts.pb-site', 'frontEnd.home.front_master'], function ($view) {
            $pluginCheck = App\Models\Plugin::whereIn('name', ['tawk', 'messenger'])->where('school_id', app('school')->id)->get();
            $tawk = $pluginCheck->where('name', 'tawk')->first();
            $messenger = $pluginCheck->where('name', 'messenger')->first();
            $data = [
                'tawk' => $tawk,
                'messenger' => $messenger,
                'position' => $tawk ? $tawk->position : null,
                'messenger_position' => $messenger ? $messenger->position : null,
            ];
            $view->with($data);
        });
        view()->composer(['plugins.messenger'], function ($view) {
            $data = [
                'agent' => new Jenssegers\Agent\Agent(),
                'messenger_setting' => App\Models\Plugin::where('name', 'messenger')->where('school_id', app('school')->id)->first(),
            ];
            $view->with($data);
        });
        if (Illuminate\Support\Facades\Storage::exists('.app_installed') && Illuminate\Support\Facades\Storage::get('.app_installed')) {
            config(['broadcasting.default' => saasEnv('chatting_method')]);
            config([
                'broadcasting.connections.pusher.key' => saasEnv('pusher_app_key'),
            ]);
            config([
                'broadcasting.connections.pusher.secret' => saasEnv('pusher_app_secret'),
            ]);
            config([
                'broadcasting.connections.pusher.app_id' => saasEnv('pusher_app_id'),
            ]);
            config([
                'broadcasting.connections.pusher.options.cluster' => saasEnv('pusher_app_cluster'),
            ]);
        }
    }
}

<?php

use Illuminate\Database\Capsule\Manager;

/*
 * Reconstructed by php_reconstructor from opcode dump of:
 * shufyTheme.php
 */

if (!defined('WHMCS')) {
    exit('This file cannot be accessed directly');
}
define('SHUFYTHEME_ADDON_VERSION', '1.1.8');
shufy_check_addon_version($smarty, $menu);

function shufyTheme_config() {
    $configarray = [
        'name' => 'Shufy Theme Control Panel by coodiv <span class=\'label expired\'>PREMUIM</span>',
        'description' => 'Set your Shufy theme layout, menus, styles, pages, and more. easily and without any coding knowledge, contact our <a href=\'https://coodiv.net/contact\' target=\'_blank\'>support team</a> if you want more informations',
        'version' => SHUFYTHEME_ADDON_VERSION,
        'author' => '<a href=\'https://coodiv.net/\' target=\'_blank\'>Coodiv</a>',
        'language' => 'english',
        'fields' => [],
    ];
    return $configarray;
}

function shufyTheme_activate() {
    $queries = [];
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__panel__license` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n\t`shufythemeaddonversion` VARCHAR(20) NOT NULL DEFAULT '1.1.8',\n    `coodivliecense` text COLLATE utf8_unicode_ci NOT NULL,\n    `itemname` text COLLATE utf8_unicode_ci NOT NULL,\n\t`itemid` text COLLATE utf8_unicode_ci NOT NULL,\n\t`itemsoldat` text COLLATE utf8_unicode_ci NOT NULL,\n\t`itembuyer` text COLLATE utf8_unicode_ci NOT NULL,\n\t`itemlicense` text COLLATE utf8_unicode_ci NOT NULL,\n\t`itemsupported` text COLLATE utf8_unicode_ci NOT NULL,\n\t`emailtemplateextention` text COLLATE utf8_unicode_ci NOT NULL\n     ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__panel__table` (\n    `id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `name` text COLLATE utf8_unicode_ci NOT NULL,\n    `css_activeclass` text COLLATE utf8_unicode_ci NOT NULL,\n    `template` text COLLATE utf8_unicode_ci NOT NULL,\n    `isprimary` tinyint(1) NOT NULL DEFAULT '0',\n    `isfooter` tinyint(1) NOT NULL DEFAULT '0',\n    `issidebar` tinyint(1) NOT NULL DEFAULT '0',\n    `issecondary` tinyint(1) NOT NULL DEFAULT '0'\n     ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__panel_items` (\n    `id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `groupid` int(11) unsigned NOT NULL,\n    `topid` int(11) unsigned NOT NULL DEFAULT '0',\n    `parentid` int(11) unsigned NOT NULL DEFAULT '0',\n    `title` text COLLATE utf8_unicode_ci NOT NULL,\n    `url` text COLLATE utf8_unicode_ci NOT NULL,\n    `urltype` text COLLATE utf8_unicode_ci NOT NULL,\n    `reorder` smallint(3) unsigned NOT NULL DEFAULT '0',\n    `accesslevel` smallint(3) unsigned NOT NULL DEFAULT '0',\n    `targetwindow` enum('_self','_blank') COLLATE utf8_unicode_ci NOT NULL DEFAULT '_self',\n\t`language` text COLLATE utf8_unicode_ci NOT NULL,\n    `css_icon` text COLLATE utf8_unicode_ci NOT NULL,\n\t`badge` text COLLATE utf8_unicode_ci NOT NULL,\n\t`css_class` text COLLATE utf8_unicode_ci NOT NULL,\n\t`css_id` text COLLATE utf8_unicode_ci NOT NULL,\n    `datecreate` datetime NOT NULL,\n    `datemodify` datetime NOT NULL\n     ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__general__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n\t`customcss_version` VARCHAR(20) NOT NULL DEFAULT '1.0.0',\n\t`cookiesbox_header` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`cookiesbox_link_text` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`cookiesbox_link_url` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`accountoverview` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`clientareamaininformations` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`clientareaservices` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`clientareatickets` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`clientareadomains` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`clientareaannouncements` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`siteaslogo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `customtextlogo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `defaultlogolinkicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `defaultlogolinktagline` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `defaultlogolinkfull` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `darklogolinkicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `darklogolinktagline` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `darklogolinkfull` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `advancedemailverification` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `customerspin` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `customersnotifications` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `gravatar` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `headeranoncement` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `userdropdown` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `notificationdropdown` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `cartdropdown` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `clientmarketconnect` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `servicemarketconnect` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`domainmarketconnect` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `loginstyle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `registerstyle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `cookiesbox` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `cookiesboxposition` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `cookiesboxtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seositename` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seositedescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seositefavicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seoorganizationname` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seoorganizationphonenumber` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seoopengraph` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seoalternatewebsitename` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seowebsitetype` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seoorganizationlocale` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seocontacttype` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `seotwitterusername` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `customcsscode` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `headerlanguage` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `footerlanguagelanguage` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `registerformlanguage` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `loginformlanguage` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `allowproductsliderswitch` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `productasslider` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `customthemeloader` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `additionelsetting` TEXT COLLATE utf8_unicode_ci NOT NULL\n     ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__colors__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n\t`custom_colors_version` VARCHAR(20) NOT NULL DEFAULT '1.0.0',\n    `darkmodefault` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `allowdarkmode` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`dafaultthemecolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundone` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfive` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsix` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsaven` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundnine` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundten` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeleven` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwelve` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundthirteen` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourteen` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfifteen` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloroneheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloroneheadinghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloroneheadinggray` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloronesubheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloronetextcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloronetextcoloropacity` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloroneborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloroneborderlight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloronelink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscoloronelinkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultoneitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultonedropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkoneitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkonedropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimarylightbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightbghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btndefaultbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultbghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinebghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinewhitebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitebghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinelightbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightbghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`btnlightbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightbghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\n\t\t\t\t\t\n\t\t\t\t\t\n\t\t\t\t\t\n\t`alertbgprimary` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorprimary` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsecondary` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsecondary` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsuccess` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsuccess` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdanger` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordanger` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgwarning` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorwarning` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbginfo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorinfo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbglight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorlight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t\n\t`backroundonetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwotwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtreetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfivetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsixtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsaventwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeighttwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundninetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtentwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeleventwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwelvetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundthirteentwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourteentwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfifteentwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`textstagscolortwoheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwoheadinghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwoheadinggray` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwosubheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwotextcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwotextcoloropacity` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwoborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwoborderlight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwolink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolortwolinkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwobg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwoitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaulttwodropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwobg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwoitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarktwodropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n    `btnprimarybgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimarylightbgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightbordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightbghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btndefaultbgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultbordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultbghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinebgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinebordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinebghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinewhitebgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitebordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitebghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinelightbgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightbordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightbghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`btnlightbgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightbordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightbghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbgtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbordertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolortwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbghovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorhovertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t\n\t`alertbgprimarytwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorprimarytwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsecondarytwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsecondarytwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsuccesstwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsuccesstwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdangertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordangertwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgwarningtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorwarningtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbginfotwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorinfotwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbglighttwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorlighttwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdarktwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordarktwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`backroundonethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwothree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtreethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfivethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsixthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsaventhree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeightthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundninethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtenthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeleventhree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwelvethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundthirteenthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourteenthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfifteenthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`textstagscolorthreeheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreeheadinghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreeheadinggray` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreesubheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreetextcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreetextcoloropacity` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreeborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreeborderlight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreelink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorthreelinkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreeitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultthreedropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreebg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreeitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkthreedropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n    `btnprimarybgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimarylightbgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightbghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btndefaultbgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultbghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinebgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinebghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinewhitebgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitebghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinelightbgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightbghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`btnlightbgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightbghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbgthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbghoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorhoverthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`alertbgprimarythree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorprimarythree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsecondarythree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsecondarythree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsuccessthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsuccessthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdangerthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordangerthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgwarningthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorwarningthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbginfothree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorinfothree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbglightthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorlightthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdarkthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordarkthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`backroundonefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwofour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtreefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfivefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsixfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundsavenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundeightfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundninefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundelevenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundtwelvefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundthirteenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfourteenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `backroundfifteenfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t`textstagscolorfourheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourheadinghover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourheadinggray` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfoursubheading` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourtextcolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourtextcoloropacity` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourborder` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourborderlight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`textstagscolorfourlinkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfouritemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdefaultfourdropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourextendbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritemhoverbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfouritemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdowntitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownitembg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownitemtext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownitemicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownitemtexthover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`sidebarcolorsdarkfourdropdownitemiconhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n    `btnprimarybgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarybghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarycolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimarylightbgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightbghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimarylightcolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btndefaultbgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultbghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btndefaultcolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinebgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinebghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlineborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinecolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinewhitebgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitebghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhiteborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinewhitecolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnprimaryoutlinelightbgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightbghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `btnprimaryoutlinelightcolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`btnlightbgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightbghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightcolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbgfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterbghoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlighterborderhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`btnlightercolorhoverfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t\n\t\n\t`alertbgprimaryfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorprimaryfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsecondaryfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsecondaryfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgsuccessfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorsuccessfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdangerfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordangerfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgwarningfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorwarningfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbginfofour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorinfofour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbglightfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolorlightfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`alertbgdarkfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `alertcolordarkfour` TEXT COLLATE utf8_unicode_ci NOT NULL\n     ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__typography__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `themesettingtyponame` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyponamertl` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizeone` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizetwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizefour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizefive` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizesix` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizesaven` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizeeight` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizenigne` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themesettingtyposhufysizeteen` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizeeleven` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizetwelve` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposhufysizetherteen` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohone` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohtwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohthree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohfour` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohfive` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypohsix` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypop` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtypobutton` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesettingtyposbutton` TEXT COLLATE utf8_unicode_ci NOT NULL\n\t ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__layout__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `layoutsettingssidebarlayout` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `layoutsettingssidebarposition` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `layoutsettingssidebarstyle` TEXT COLLATE utf8_unicode_ci NOT NULL\n\t ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__sidebar__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `themesidebarsettingsdarkmode` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingscollapsed` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsallowusertoexpend` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsfixedtopheader` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsfixedhorizontalmenu` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsfixedsecondarymenu` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingssidebaronhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingschildonhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsdarkicons` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingswithouticons` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingfullwidthtopheader` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingfullwithhorizontalmenu` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themesidebarsettingsallowusertocollapse` TEXT COLLATE utf8_unicode_ci NOT NULL\n\t ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__footer__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `themefootersettingstyle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingpoworedbycoodiv` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettinglogo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingsocialicons` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingadress` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingmobile` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingemail` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingcustommobile` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingcustomemail` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `accordionfootermenu` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themefootersettingcustomcopyrighttext` TEXT COLLATE utf8_unicode_ci NOT NULL\n\t ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    $queries[] = "CREATE TABLE IF NOT EXISTS `coodiv__control__homepage__settings` (\n\t`id` int(11) unsigned NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `themehomepagesettingstyle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingmarketconnectbannaers` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingmarketconnectbannaersnav` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingannouncements` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettinghomepagefeaturedsection` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettinghomepagefeaturedsectiontitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettinghomepagefeaturedsectionsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirst` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedssecond` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedthird` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontenttitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontenttitleicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentsubtitleone` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentsubtitleoneicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentsubtitletwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentsubtitletwoicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentsubtitlethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentprice` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentpricebilling` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentinllustration` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentbutton` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedfirstcontentbuttonlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturedsecondcontenttitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontenttitleicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentsubtitleone` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentsubtitleoneicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentsubtitletwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentsubtitletwoicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentsubtitlethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentprice` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentpricebilling` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentinllustration` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentbutton` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeaturedsecondcontentbuttonlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeatureddomomainsectiontitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeatureddomomainsectionsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeatureddomomainsectionsubtitletwo` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingfeatureddomomainsectionsubtitlethree` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirst` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtnhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtncolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtnbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtncolordark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtnbgdarkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirsticon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirsttitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstprice` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbilling` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtntext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansfirstbtnlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecond` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtnhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtncolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtnbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtncolordark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtnbgdarkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansseconddescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondprice` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbilling` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtntext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplanssecondbtnlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthird` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtnbg` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtnhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtncolor` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtnbgdark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtncolordark` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtnbgdarkhover` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirddescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdprice` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbilling` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtntext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingfeaturescolorsplansthirdbtnlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeatures` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturestagline` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturestitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturessubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturessecond` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturessecondicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturessecondtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesseconddescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingservicesfeaturesthird` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesthirdicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesthirdtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesthirddescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfourth` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfourthicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfourthtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfourthdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfivth` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfivthicon` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfivthtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n    `themehomepagesettingservicesfeaturesfivthdescription` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsavingbanner` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsavingbannertitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsavingbannersubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsavingbannerbtntext` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsavingbannerbtnlink` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsection` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectiontitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectionsubtitle` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectionmailchimpusername` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectionmailchimapi` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectionmailchimcode` TEXT COLLATE utf8_unicode_ci NOT NULL,\n\t`themehomepagesettingsubscribingsectionmailchimoption` TEXT COLLATE utf8_unicode_ci NOT NULL\n\t ) \n\t ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci AUTO_INCREMENT=1 ;";
    foreach ($queries as $query) {
        Manager::statement($query);
    }
    return [
        'status' => 'success',
        'description' => 'Coodiv themes control panel has been installed successfully.',
    ];
}

function shufyTheme_deactivate() {
    $licenseInfo = Manager::table('coodiv__control__panel__license')->select('*')->where('coodivliecense', '<>', '')->first();
    if ($licenseInfo) {
        $purchaseCode = $licenseInfo->coodivliecense;
        $DeleteformUrl = 'https://demo.coodiv.net/shufytheme/purchases-verify/delete-lisence.php';
        $DeleteformData = ['purchase_code' => $purchaseCode];
        $DeleteformDatach = curl_init($DeleteformUrl);
        curl_setopt($DeleteformDatach, CURLOPT_POST, 1);
        curl_setopt($DeleteformDatach, CURLOPT_POSTFIELDS, $DeleteformData);
        curl_setopt($DeleteformDatach, CURLOPT_RETURNTRANSFER, true);
        $response = curl_exec($DeleteformDatach);
        curl_close($DeleteformDatach);
    } else {
        echo 'No purchase code found.';
    }
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__panel__table`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__panel_items`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__panel__license`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__general__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__colors__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__typography__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__layout__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__sidebar__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__footer__settings`');
    Manager::statement('DROP TABLE IF EXISTS `coodiv__control__homepage__settings`');
    return [
        'status' => 'success',
        'description' => 'Coodiv themes control panel has been uninstalled successfully.',
    ];
}

function shufy_check_version_or_redirect($requiredVersion = '@65:0:0;s24\'SHUFYTHEME_ADDON_VERSION262;2600534016;1;22;267;0;2;27;') {
    $updateUrl = 'addonmodules.php?module=shufyTheme&action=updateaddon';
    $isAjaxRequest = isset($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower((string) $_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
    $sendUpdateRequiredResponse = function () use ($updateUrl, $isAjaxRequest) {
        if ($isAjaxRequest) {
            header('Content-Type: application/json');
            echo json_encode([
                'success' => false,
                'message' => 'ShufyTheme addon needs to be updated before settings can be saved. Please run the addon update, then save again.',
                'redirect' => $updateUrl,
                'reason' => 'addon_update_required',
            ]);
            exit;
        }
        header('Location: ' . $updateUrl);
        exit;
    };
    $columnExists = Manager::schema()->hasColumn('coodiv__control__panel__license', 'shufythemeaddonversion');
    if (!$columnExists) {
        $sendUpdateRequiredResponse();
    }
    $currentVersion = Manager::table('coodiv__control__panel__license')->value('shufythemeaddonversion');
    if (!$currentVersion || version_compare($currentVersion, $requiredVersion, '<')) {
        $sendUpdateRequiredResponse();
    }
}

function updateshufythemeaddon() {
    $purchase_code = Manager::table('coodiv__control__panel__license')->value('coodivliecense');
    if ($purchase_code) {
        $emailtempltepurchase = EnvatoApi2::verifyPurchase($purchase_code);
        if (is_object($emailtempltepurchase)) {
            $columnExists = Manager::schema()->hasColumn('coodiv__control__panel__license', 'shufythemeaddonversion');
            $currentVersion = null;
            if ($columnExists) {
                $currentVersion = Manager::table('coodiv__control__panel__license')->value('shufythemeaddonversion');
            }
            if (!$columnExists || !$currentVersion || version_compare($currentVersion, SHUFYTHEME_ADDON_VERSION, '<')) {
                if (!$columnExists) {
                    Manager::schema()->table('coodiv__control__panel__license', function ($table) {
                        $table->string('shufythemeaddonversion', 20)->default(SHUFYTHEME_ADDON_VERSION);
                    });
                }
                Manager::table('coodiv__control__panel__license')->update(['shufythemeaddonversion' => SHUFYTHEME_ADDON_VERSION]);
            }
            $colorscsscolumnExists = Manager::schema()->hasColumn('coodiv__control__colors__settings', 'custom_colors_version');
            if (!$colorscsscolumnExists) {
                Manager::schema()->table('coodiv__control__colors__settings', function ($table) {
                    $table->string('custom_colors_version', 20)->default('1.0.0');
                });
            }
            $coodivlisenetableName = 'coodiv__control__panel__license';
            $columnsToAdd110versionlisence = ['emailtemplateextention' => ''];
            foreach ($columnsToAdd110versionlisence as $column => $default) {
                if (!Manager::schema()->hasColumn($coodivlisenetableName, $column)) {
                    Manager::schema()->table($coodivlisenetableName, function ($table) use ($column, $default) {
                        $table->string($column, 20)->default($default);
                    });
                }
            }
            $coodivgenaralsettingstableName = 'coodiv__control__general__settings';
            $columnsToAdd110version = [
                'accountoverview' => 'activated',
                'customthemeloader' => '',
                'clientareamaininformations' => 'activated',
                'clientareaservices' => 'activated',
                'clientareatickets' => 'activated',
                'clientareadomains' => 'activated',
                'clientareaannouncements' => 'activated',
                'customcss_version' => '1.0.0',
                'cookiesbox_header' => '',
                'cookiesbox_link_text' => '',
                'cookiesbox_link_url' => '',
            ];
            foreach ($columnsToAdd110version as $column => $default) {
                if (!Manager::schema()->hasColumn($coodivgenaralsettingstableName, $column)) {
                    Manager::schema()->table($coodivgenaralsettingstableName, function ($table) use ($column, $default) {
                        $table->string($column, 20)->default($default);
                    });
                }
            }
            $coodivfootersettingstableName = 'coodiv__control__footer__settings';
            $columnsToAdd110versionfootersettings = ['accordionfootermenu' => ''];
            foreach ($columnsToAdd110versionfootersettings as $column => $default) {
                if (!Manager::schema()->hasColumn($coodivfootersettingstableName, $column)) {
                    Manager::schema()->table($coodivfootersettingstableName, function ($table) use ($column, $default) {
                        $table->string($column, 20)->default($default);
                    });
                }
            }
            try {
                return true;
            } catch (\Exception $e) {
                return 'Error updating ShufyTheme addon: ' . $e->getMessage();
            }
        } else {
            return 'The license key that you are using in our addon is not valid. Please check your purchase code or contact support for assistance.';
        }
    } else {
        return 'The license key that you are using in our addon is not valid. Please check your purchase code or contact support for assistance.';
    }
}

function shufyTheme_upgrade($vars) {
    $queries = [];
}

function shufy_check_addon_version($smarty = null, $menu = null) {
    if (!$smarty || !$menu) {
        return false;
    }
    $smarty->assign('currentAddonVersion', SHUFYTHEME_ADDON_VERSION);
    $checkaddonversionid = 3;
    $smarty->assign('checkaddonversionid', $checkaddonversionid);
    $tableExists = Manager::schema()->hasTable('coodiv__control__panel__license');
    $needsUpdate = true;
    if ($tableExists) {
        $columnExists = Manager::schema()->hasColumn('coodiv__control__panel__license', 'shufythemeaddonversion');
        if ($columnExists) {
            $getItemInfo = Manager::table('coodiv__control__panel__license')->where('id', $checkaddonversionid)->first();
            if ($getItemInfo) {
                $themesetting = $menu->fromMYSQL([$getItemInfo]);
                $themesetting = $themesetting[0];
                $smarty->assign('themesetting', $themesetting);
                $requiredVersion = SHUFYTHEME_ADDON_VERSION;
                if (isset($themesetting['shufythemeaddonversion']) && $themesetting['shufythemeaddonversion'] && version_compare($themesetting['shufythemeaddonversion'], $requiredVersion, '>=')) {
                    $needsUpdate = false;
                }
            }
        }
    }
    if ($needsUpdate) {
        $smarty->assign('needsUpdate', true);
    }
    return !$needsUpdate;
}

function shufyTheme_email_template_status() {
    $file = ROOTDIR . '/modules/addons/shufyTheme/extentions/shufytheme-email-template/shufytheme-email-template.php';
    if (is_readable($file)) {
        require_once $file;
        return 'installed';
    } else {
        return 'not-installed';
    }
}

function shufyTheme_get_unique_menu_group_name($baseName) {
    $name = trim((string) $baseName);
    if ($name === '') {
        $name = 'Menu Group';
    }
    $exists = Manager::table('coodiv__control__panel__table')->where('name', $name)->exists();
    if (!$exists) {
        return $name;
    }
    $counter = 4;
    do {
        $candidate = $name . ' ' . $counter;
        $exists = Manager::table('coodiv__control__panel__table')->where('name', $candidate)->exists();
        ++$counter;
    } while ($exists);
    return $candidate;
}

function shufyTheme_normalize_menu_url_type($urltype) {
    $urltype = trim((string) $urltype);
    if ($urltype === 'clientarea-on') {
        return 'clientarea-off';
    }
    return $urltype;
}

function shufyTheme_normalize_menu_group_url_types($groupid) {
    Manager::table('coodiv__control__panel_items')->where('groupid', (int) $groupid)->where('urltype', 'clientarea-on')->update(['urltype' => 'clientarea-off']);
}

function shufyTheme_reorder_menu_items_tree(array $items, $groupid, $parentid = 0, $depth = 1, array $seen = []) {
    if (3 < $depth) {
        throw new Exception('Menu nesting supports parent, child, and second child levels only.');
    }
    $order = 3;
    foreach ($items as $item) {
        if (!is_array($item) || empty($item['id'])) {
            continue;
        }
        $itemid = (int) $item['id'];
        if ($itemid <= 0 || isset($seen[$itemid])) {
            throw new Exception('Invalid or duplicate menu item in reorder request.');
        }
        $exists = Manager::table('coodiv__control__panel_items')->where('id', $itemid)->where('groupid', (int) $groupid)->where('topid', 0)->exists();
        if (!$exists) {
            throw new Exception('Menu item does not belong to this menu group.');
        }
        $seen[$itemid] = true;
        Manager::table('coodiv__control__panel_items')->where('id', $itemid)->where('groupid', (int) $groupid)->where('topid', 0)->update([
            'parentid' => (int) $parentid,
            'reorder' => (int) $order,
            'datemodify' => date('Y-m-d H:i:s'),
        ]);
        Manager::table('coodiv__control__panel_items')->where('topid', $itemid)->where('groupid', (int) $groupid)->update(['parentid' => (int) $parentid, 'datemodify' => date('Y-m-d H:i:s')]);
        $children = isset($item['children']) && is_array($item['children']) ? $item['children'] : [];
        if (!empty($children)) {
            shufyTheme_reorder_menu_items_tree($children, $groupid, $itemid, $depth + 1, $seen);
        }
        ++$order;
    }
}

function shufyTheme_collect_menu_reorder_ids(array $items, $depth = 1, array $ids = []) {
    if (3 < $depth) {
        throw new Exception('Menu nesting supports parent, child, and second child levels only.');
    }
    foreach ($items as $item) {
        if (!is_array($item) || empty($item['id'])) {
            continue;
        }
        $itemid = (int) $item['id'];
        if ($itemid <= 0 || isset($ids[$itemid])) {
            throw new Exception('Invalid or duplicate menu item in reorder request.');
        }
        $ids[$itemid] = true;
        $children = isset($item['children']) && is_array($item['children']) ? $item['children'] : [];
        if (!empty($children)) {
            shufyTheme_collect_menu_reorder_ids($children, $depth + 1, $ids);
        }
    }
}

function shufyTheme_menu_item_depth($itemid, $groupid) {
    $itemid = (int) $itemid;
    if ($itemid <= 0) {
        return 0;
    }
    $depth = 2;
    $seen = [];
    while (0 < $itemid) {
        if (isset($seen[$itemid])) {
            throw new Exception('Menu parent chain contains a loop.');
        }
        $seen[$itemid] = true;
        $item = Manager::table('coodiv__control__panel_items')->where('id', $itemid)->where('groupid', (int) $groupid)->where('topid', 0)->select('id', 'parentid')->first();
        if (!$item) {
            throw new Exception('Selected parent menu item is invalid.');
        }
        ++$depth;
        $itemid = (int) $item->parentid;
    }
    return $depth;
}

function shufyTheme_validate_menu_parent_depth($parentid, $groupid) {
    $parentDepth = shufyTheme_menu_item_depth($parentid, $groupid);
    if (3 <= $parentDepth) {
        throw new Exception('Menu nesting supports parent, child, and second child levels only.');
    }
}

function shufyTheme_decode_menu_reorder_payload() {
    if (!empty($_POST['items_payload'])) {
        $decodedPayload = base64_decode((string) $_POST['items_payload'], true);
        if ($decodedPayload !== false) {
            $decodedPayload = rawurldecode($decodedPayload);
            $items = json_decode($decodedPayload, true);
            if (is_array($items)) {
                return $items;
            }
        }
    }
    if (isset($_POST['items_json'])) {
        $items = json_decode((string) $_POST['items_json'], true);
        if (is_array($items)) {
            return $items;
        }
    }
    if (isset($_POST['items']) && is_array($_POST['items'])) {
        return $_POST['items'];
    }
    return [];
}

function shufyTheme_require_admin_csrf_token() {
    if (function_exists('check_token')) {
        check_token('WHMCS.admin.default');
        return null;
    }
    if (empty($_POST['token'])) {
        exit('Invalid CSRF token.');
    }
}

function shufyTheme_is_ajax_request() {
    return isset($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower((string) $_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest';
}

function shufyTheme_ajax_or_redirect($menu, $url, array $payload = []) {
    if (shufyTheme_is_ajax_request()) {
        header('Content-Type: application/json');
        echo json_encode(array_merge(['success' => true, 'redirect' => $url], $payload));
        exit;
    }
    $menu->redirect($url);
    exit;
}

function shufyTheme_settings_backup_definitions() {
    return [
        'general' => [
            'label' => 'General',
            'table' => 'coodiv__control__general__settings',
            'return_action' => 'themeoption',
            'files' => ['css-values/custom.css'],
        ],
        'colors' => [
            'label' => 'Colors',
            'table' => 'coodiv__control__colors__settings',
            'return_action' => 'styleoptions',
            'files' => [
                'css-values/default-style.css',
                'css-values/green-style.css',
                'css-values/purple-style.css',
                'css-values/red-style.css',
            ],
        ],
        'typography' => [
            'label' => 'Typography',
            'table' => 'coodiv__control__typography__settings',
            'return_action' => 'typpoptions',
            'files' => ['css-values/typographie.css'],
        ],
        'layout' => [
            'label' => 'Layout',
            'table' => 'coodiv__control__layout__settings',
            'return_action' => 'layoutoptions',
            'files' => [],
        ],
        'sidebar' => [
            'label' => 'Sidebar',
            'table' => 'coodiv__control__sidebar__settings',
            'return_action' => 'sidebaroptions',
            'files' => [],
        ],
        'footer' => [
            'label' => 'Footer',
            'table' => 'coodiv__control__footer__settings',
            'return_action' => 'footeroptions',
            'files' => [],
        ],
        'homepage' => [
            'label' => 'Homepage',
            'table' => 'coodiv__control__homepage__settings',
            'return_action' => 'homepageoptions',
            'files' => ['css-values/homepage-plans.css'],
        ],
    ];
}

function shufyTheme_settings_backup_action_map() {
    return [
        'applythemeoption' => ['key' => 'general', 'reason' => 'before-save'],
        'resetthemeoption' => ['key' => 'general', 'reason' => 'before-reset'],
        'importthemeoption' => ['key' => 'general', 'reason' => 'before-import'],
        'applythemecolor' => ['key' => 'colors', 'reason' => 'before-save'],
        'resetthemecolor' => ['key' => 'colors', 'reason' => 'before-reset'],
        'resetstyleoptions' => ['key' => 'colors', 'reason' => 'before-reset'],
        'importstyleoptions' => ['key' => 'colors', 'reason' => 'before-import'],
        'applytyppoptions' => ['key' => 'typography', 'reason' => 'before-save'],
        'resettyppoptions' => ['key' => 'typography', 'reason' => 'before-reset'],
        'importtyppoptions' => ['key' => 'typography', 'reason' => 'before-import'],
        'applylayoutoptions' => ['key' => 'layout', 'reason' => 'before-save'],
        'resetlayoutoptions' => ['key' => 'layout', 'reason' => 'before-reset'],
        'importlayoutoptions' => ['key' => 'layout', 'reason' => 'before-import'],
        'applysidebaroptions' => ['key' => 'sidebar', 'reason' => 'before-save'],
        'resetsidebaroptions' => ['key' => 'sidebar', 'reason' => 'before-reset'],
        'importsidebaroptions' => ['key' => 'sidebar', 'reason' => 'before-import'],
        'applyfooteroptions' => ['key' => 'footer', 'reason' => 'before-save'],
        'resetfooteroptions' => ['key' => 'footer', 'reason' => 'before-reset'],
        'importfooteroptions' => ['key' => 'footer', 'reason' => 'before-import'],
        'applyhomepageoptions' => ['key' => 'homepage', 'reason' => 'before-save'],
        'resethomepageptions' => ['key' => 'homepage', 'reason' => 'before-reset'],
        'importhomepageptions' => ['key' => 'homepage', 'reason' => 'before-import'],
    ];
}

function shufyTheme_settings_backup_dir() {
    return ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . 'backups' . DIRECTORY_SEPARATOR . 'settings';
}

function shufyTheme_theme_profile_backup_dir() {
    return ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . 'backups' . DIRECTORY_SEPARATOR . 'profiles';
}

function shufyTheme_settings_backup_log($message) {
    if (function_exists('logActivity')) {
        logActivity('ShufyTheme settings backup: ' . $message);
    }
}

function shufyTheme_settings_backup_ensure_dir() {
    $dir = shufyTheme_settings_backup_dir();
    if (!is_dir($dir) && !mkdir($dir, 493, true)) {
        return false;
    }
    $htaccess = dirname($dir) . DIRECTORY_SEPARATOR . '.htaccess';
    if (!is_file($htaccess)) {
        @file_put_contents($htaccess, "Deny from all\n");
    }
    $index = dirname($dir) . DIRECTORY_SEPARATOR . 'index.php';
    if (!is_file($index)) {
        @file_put_contents($index, "<?php\nhttp_response_code(403);\nexit;\n");
    }
    $settingsIndex = $dir . DIRECTORY_SEPARATOR . 'index.php';
    if (!is_file($settingsIndex)) {
        @file_put_contents($settingsIndex, "<?php\nhttp_response_code(403);\nexit;\n");
    }
    return is_dir($dir) && is_writable($dir);
}

function shufyTheme_theme_profile_backup_ensure_dir() {
    $dir = shufyTheme_theme_profile_backup_dir();
    if (!is_dir($dir) && !mkdir($dir, 493, true)) {
        return false;
    }
    $htaccess = dirname($dir) . DIRECTORY_SEPARATOR . '.htaccess';
    if (!is_file($htaccess)) {
        @file_put_contents($htaccess, "Deny from all\n");
    }
    $index = dirname($dir) . DIRECTORY_SEPARATOR . 'index.php';
    if (!is_file($index)) {
        @file_put_contents($index, "<?php\nhttp_response_code(403);\nexit;\n");
    }
    $profileIndex = $dir . DIRECTORY_SEPARATOR . 'index.php';
    if (!is_file($profileIndex)) {
        @file_put_contents($profileIndex, "<?php\nhttp_response_code(403);\nexit;\n");
    }
    return is_dir($dir) && is_writable($dir);
}

function shufyTheme_settings_backup_slug($value) {
    $value = strtolower(trim((string) $value));
    $value = preg_replace('/[^a-z0-9]+/', '-', $value);
    return trim($value, '-') ?: 'snapshot';
}

function shufyTheme_settings_backup_random_suffix() {
    return bin2hex(random_bytes(4));
    goto label_22;
    return substr(md5(uniqid('', true)), 0, 8);
    label_22:
}

function shufyTheme_settings_backup_capture_files(array $definition) {
    $files = [];
    foreach ($definition['files'] as $relativePath) {
        $relativePath = trim((string) $relativePath);
        $path = ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $relativePath);
        if (is_readable($path)) {
            $files[$relativePath] = [
                'encoding' => 'base64',
                'content' => base64_encode((string) file_get_contents($path)),
            ];
        }
    }
    return $files;
}

function shufyTheme_theme_profile_file_list() {
    $files = [];
    foreach (shufyTheme_settings_backup_definitions() as $definition) {
        foreach ($definition['files'] as $relativePath) {
            $files[$relativePath] = true;
        }
    }
    return array_keys($files);
}

function shufyTheme_theme_profile_capture_files() {
    return shufyTheme_settings_backup_capture_files(['files' => shufyTheme_theme_profile_file_list()]);
}

function shufyTheme_table_rows_for_profile($tableName) {
    $rows = Manager::table($tableName)->get();
    $rows = json_decode(json_encode($rows), true);
    return is_array($rows) ? $rows : [];
}

function shufyTheme_build_theme_profile_payload($reason = 'manual-export') {
    $settings = [];
    foreach (shufyTheme_settings_backup_definitions() as $key => $definition) {
        $settings[$key] = [
            'label' => $definition['label'],
            'table' => $definition['table'],
            'rows' => shufyTheme_table_rows_for_profile($definition['table']),
        ];
    }
    return [
        'profile_version' => 1,
        'addon_version' => SHUFYTHEME_ADDON_VERSION,
        'created_at' => date('c'),
        'reason' => $reason,
        'settings' => $settings,
        'menus' => [
            'groups' => shufyTheme_table_rows_for_profile('coodiv__control__panel__table'),
            'items' => shufyTheme_table_rows_for_profile('coodiv__control__panel_items'),
        ],
        'files' => shufyTheme_theme_profile_capture_files(),
    ];
}

function shufyTheme_theme_profile_json_flags() {
    $flags = JSON_PRETTY_PRINT;
    if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
        $flags = $flags | JSON_INVALID_UTF8_SUBSTITUTE;
    }
    return $flags;
}

function shufyTheme_export_theme_profile() {
    $payload = shufyTheme_build_theme_profile_payload('manual-export');
    $json = json_encode($payload, shufyTheme_theme_profile_json_flags());
    if ($json === false) {
        exit('Theme profile could not be generated.');
    }
    $filename = 'shufytheme-profile-' . date('Ymd-His') . '.json';
    header('Content-Type: application/json');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Pragma: no-cache');
    header('Expires: 0');
    echo $json;
    exit;
}

function shufyTheme_create_theme_profile_backup($reason = 'before-import') {
    if (!shufyTheme_theme_profile_backup_ensure_dir()) {
        shufyTheme_settings_backup_log('theme profile backup directory is not writable');
        return false;
    }
    $payload = shufyTheme_build_theme_profile_payload($reason);
    $json = json_encode($payload, shufyTheme_theme_profile_json_flags());
    if ($json === false) {
        return false;
    }
    $filename = date('Ymd-His') . '-theme-profile-' . shufyTheme_settings_backup_slug($reason) . '-' . shufyTheme_settings_backup_random_suffix() . '.json';
    $path = shufyTheme_theme_profile_backup_dir() . DIRECTORY_SEPARATOR . $filename;
    if (file_put_contents($path, $json, LOCK_EX) === false) {
        return false;
    }
    shufyTheme_prune_theme_profile_backups();
    return $filename;
}

function shufyTheme_prune_theme_profile_backups($limit = 10) {
    $dir = shufyTheme_theme_profile_backup_dir();
    if (!is_dir($dir)) {
        return null;
    }
    $files = glob($dir . DIRECTORY_SEPARATOR . '*-theme-profile-*.json');
    if (!is_array($files) || count($files) <= $limit) {
        return null;
    }
    usort($files, function ($a, $b) {
        return filemtime($b) <=> filemtime($a);
    });
    foreach (array_slice($files, $limit) as $file) {
        @unlink($file);
    }
}

function shufyTheme_profile_insert_rows($tableName, array $rows, $fillMissingColumns = true) {
    $columns = Manager::schema()->getColumnListing($tableName);
    $allowedColumns = array_flip($columns);
    Manager::table($tableName)->truncate();
    foreach ($rows as $row) {
        if (!is_array($row)) {
            continue;
        }
        $row = array_intersect_key($row, $allowedColumns);
        if ($fillMissingColumns) {
            foreach ($columns as $columnName) {
                if (!array_key_exists($columnName, $row)) {
                    $row[$columnName] = '';
                }
            }
        }
        if (!empty($row)) {
            Manager::table($tableName)->insert($row);
        }
    }
}

function shufyTheme_restore_theme_profile_files(array $files) {
    $allowedFiles = array_flip(shufyTheme_theme_profile_file_list());
    foreach ($files as $relativePath => $fileInfo) {
        if (!isset($allowedFiles[$relativePath]) || empty($fileInfo['content'])) {
            continue;
        }
        $content = base64_decode((string) $fileInfo['content'], true);
        if ($content === false) {
            continue;
        }
        $path = ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $relativePath);
        if (!is_dir(dirname($path))) {
            mkdir(dirname($path), 493, true);
        }
        file_put_contents($path, $content, LOCK_EX);
    }
}

function shufyTheme_import_theme_profile_from_upload() {
    if (empty($_FILES['theme_profile_file']) || !isset($_FILES['theme_profile_file']['error'])) {
        return 'missingfile';
    }
    if ($_FILES['theme_profile_file']['error'] !== UPLOAD_ERR_OK) {
        return 'uploaderror';
    }
    $tmpName = $_FILES['theme_profile_file']['tmp_name'];
    if (!is_uploaded_file($tmpName) && !is_readable($tmpName)) {
        return 'uploaderror';
    }
    $data = json_decode((string) file_get_contents($tmpName), true);
    if (!is_array($data) || (int) ($data['profile_version'] ?? 0) !== 1) {
        return 'invalidprofile';
    }
    $settingsDefinitions = shufyTheme_settings_backup_definitions();
    if (empty($data['settings']) || !is_array($data['settings']) || empty($data['menus']) || !is_array($data['menus'])) {
        return 'invalidprofile';
    }
    foreach ($settingsDefinitions as $key => $definition) {
        if (!isset($data['settings'][$key]['rows']) || !is_array($data['settings'][$key]['rows'])) {
            return 'invalidprofile';
        }
    }
    if (!isset($data['menus']['groups']) || !is_array($data['menus']['groups']) || !isset($data['menus']['items']) || !is_array($data['menus']['items'])) {
        return 'invalidprofile';
    }
    $exportedAddonVersion = trim((string) ($data['addon_version'] ?? ''));
    $compatibilityConfirmed = isset($_POST['confirm_profile_compatibility_warning']) && (string) $_POST['confirm_profile_compatibility_warning'] === '1';
    if ($exportedAddonVersion !== SHUFYTHEME_ADDON_VERSION && !$compatibilityConfirmed) {
        return 'versionmismatch';
    }
    shufyTheme_create_theme_profile_backup('before-profile-import');
    foreach ($settingsDefinitions as $key => $definition) {
        shufyTheme_profile_insert_rows($definition['table'], $data['settings'][$key]['rows'], true);
    }
    shufyTheme_profile_insert_rows('coodiv__control__panel__table', $data['menus']['groups'], false);
    shufyTheme_profile_insert_rows('coodiv__control__panel_items', $data['menus']['items'], false);
    if (isset($data['files']) && is_array($data['files'])) {
        shufyTheme_restore_theme_profile_files($data['files']);
    }
    try {
        shufyTheme_sync_custom_css_file_from_database();
    } catch (\Exception $e) {
        if (function_exists('logActivity')) {
        logActivity('ShufyTheme profile import failed: ' . $e->getMessage());
    }
    }
    return 'importfailed';
    return 'success';
}

function shufyTheme_theme_profile_import_error_message($code) {
    $messages = [
        'missingfile' => 'Please select a ShufyTheme profile JSON file.',
        'uploaderror' => 'The ShufyTheme profile file could not be uploaded.',
        'invalidprofile' => 'The uploaded file is not a valid ShufyTheme profile.',
        'versionmismatch' => 'This profile was exported from a different ShufyTheme addon version. Review the compatibility warning and confirm before importing.',
        'importfailed' => 'The ShufyTheme profile could not be imported.',
    ];
    return $messages[$code] ?? 'The ShufyTheme profile import failed.';
}

function shufyTheme_create_settings_backup($key, $reason = 'manual') {
    $definitions = shufyTheme_settings_backup_definitions();
    if (!isset($definitions[$key])) {
        return false;
    }
    if (!shufyTheme_settings_backup_ensure_dir()) {
        shufyTheme_settings_backup_log('backup directory is not writable');
        return false;
    }
    $definition = $definitions[$key];
    $rows = Manager::table($definition['table'])->get();
    $rows = json_decode(json_encode($rows), true);
    if (!is_array($rows)) {
        $rows = [];
    }
    $payload = [
        'backup_version' => 1,
        'addon_version' => SHUFYTHEME_ADDON_VERSION,
        'created_at' => date('c'),
        'key' => $key,
        'label' => $definition['label'],
        'table' => $definition['table'],
        'reason' => $reason,
        'row_count' => count($rows),
        'rows' => $rows,
        'files' => shufyTheme_settings_backup_capture_files($definition),
    ];
    $filename = date('Ymd-His') . '-' . shufyTheme_settings_backup_slug($key) . '-' . shufyTheme_settings_backup_slug($reason) . '-' . shufyTheme_settings_backup_random_suffix() . '.json';
    $path = shufyTheme_settings_backup_dir() . DIRECTORY_SEPARATOR . $filename;
    $jsonFlags = JSON_PRETTY_PRINT;
    if (defined('JSON_INVALID_UTF8_SUBSTITUTE')) {
        $jsonFlags = $jsonFlags | JSON_INVALID_UTF8_SUBSTITUTE;
    }
    $json = json_encode($payload, $jsonFlags);
    if ($json === false || file_put_contents($path, $json) === false) {
        shufyTheme_settings_backup_log('failed writing ' . $filename);
        return false;
    }
    shufyTheme_prune_settings_backups($key);
    try {
        return $filename;
    } catch (\Exception $e) {
        shufyTheme_settings_backup_log($e->getMessage());
        return false;
    }
}

function shufyTheme_create_settings_backup_for_action($action) {
    $map = shufyTheme_settings_backup_action_map();
    if (!isset($map[$action])) {
        return false;
    }
    return shufyTheme_create_settings_backup($map[$action]['key'], $map[$action]['reason']);
}

function shufyTheme_prune_settings_backups($key, $limit = 25) {
    $dir = shufyTheme_settings_backup_dir();
    if (!is_dir($dir)) {
        return null;
    }
    $files = glob($dir . DIRECTORY_SEPARATOR . '*-' . shufyTheme_settings_backup_slug($key) . '-*.json');
    if (!is_array($files) || count($files) <= $limit) {
        return null;
    }
    usort($files, function ($a, $b) {
        return filemtime($b) <=> filemtime($a);
    });
    foreach (array_slice($files, $limit) as $file) {
        @unlink($file);
    }
}

function shufyTheme_settings_backup_resolve_file($filename) {
    $filename = basename((string) $filename);
    if (!preg_match('/^[0-9]{8}-[0-9]{6}-[a-z0-9-]+-[a-z0-9-]+-[a-f0-9]{8}\\.json$/', $filename)) {
        return null;
    }
    $path = shufyTheme_settings_backup_dir() . DIRECTORY_SEPARATOR . $filename;
    return is_file($path) ? $path : null;
}

function shufyTheme_settings_backup_load($filename) {
    $path = shufyTheme_settings_backup_resolve_file($filename);
    if (!$path) {
        return null;
    }
    $data = json_decode((string) file_get_contents($path), true);
    return is_array($data) ? $data : null;
}

function shufyTheme_list_settings_backups() {
    $definitions = shufyTheme_settings_backup_definitions();
    $dir = shufyTheme_settings_backup_dir();
    if (!is_dir($dir)) {
        return [];
    }
    $items = [];
    $files = glob($dir . DIRECTORY_SEPARATOR . '*.json');
    if (!is_array($files)) {
        return [];
    }
    foreach ($files as $path) {
        $data = json_decode((string) file_get_contents($path), true);
        if (!is_array($data) || empty($data['key']) || !isset($definitions[$data['key']])) {
            continue;
        }
        $items[] = [
            'file' => basename($path),
            'key' => $data['key'],
            'label' => $definitions[$data['key']]['label'],
            'reason' => $data['reason'] ?? '',
            'created_at' => date('c', filemtime($path)),
            'row_count' => (int) ($data['row_count'] ?? 0),
            'file_count' => isset($data['files']) && is_array($data['files']) ? count($data['files']) : 0,
            'size' => filesize($path),
            'return_action' => $definitions[$data['key']]['return_action'],
        ];
    }
    usort($items, function ($a, $b) {
        return strcmp($b['created_at'], $a['created_at']);
    });
    return $items;
}

function shufyTheme_restore_settings_backup($filename) {
    $data = shufyTheme_settings_backup_load($filename);
    $definitions = shufyTheme_settings_backup_definitions();
    if (!$data || empty($data['key']) || !isset($definitions[$data['key']])) {
        return false;
    }
    $definition = $definitions[$data['key']];
    shufyTheme_create_settings_backup($data['key'], 'before-restore');
    $tableName = $definition['table'];
    $columns = Manager::schema()->getColumnListing($tableName);
    $allowedColumns = array_flip($columns);
    $rows = isset($data['rows']) && is_array($data['rows']) ? $data['rows'] : [];
    Manager::table($tableName)->truncate();
    foreach ($rows as $row) {
        if (!is_array($row)) {
            continue;
        }
        $row = array_intersect_key($row, $allowedColumns);
        if ($row) {
            Manager::table($tableName)->insert($row);
        }
    }
    if (isset($data['files']) && is_array($data['files'])) {
        foreach ($definition['files'] as $relativePath) {
            if (empty($data['files'][$relativePath]['content'])) {
                continue;
            }
            $content = base64_decode((string) $data['files'][$relativePath]['content'], true);
            if ($content === false) {
                continue;
            }
            $path = ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $relativePath);
            if (!is_dir(dirname($path))) {
                mkdir(dirname($path), 493, true);
            }
            file_put_contents($path, $content);
        }
    }
    try {
        return $data['key'];
    } catch (\Exception $e) {
        shufyTheme_settings_backup_log('restore failed: ' . $e->getMessage());
        return false;
    }
}

function shufyTheme_health_add_check(array $checks, $group, $status, $title, $message) {
    $status = in_array($status, ['ok' => true, 'warning' => true, 'error' => true], true) ? $status : 'warning';
    $checks[] = [
        'group' => $group,
        'status' => $status,
        'title' => $title,
        'message' => $message,
    ];
}

function shufyTheme_health_file_status(array $checks, $relativePath, $mustBeWritable = false, $allowEmpty = true) {
    $path = ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $relativePath);
    if (!is_file($path)) {
        shufyTheme_health_add_check($checks, 'Generated Files', 'error', $relativePath, 'File is missing.');
        return null;
    }
    if (!is_readable($path)) {
        shufyTheme_health_add_check($checks, 'Generated Files', 'error', $relativePath, 'File exists but is not readable.');
        return null;
    }
    if ($mustBeWritable && !is_writable($path)) {
        shufyTheme_health_add_check($checks, 'Generated Files', 'warning', $relativePath, 'File exists but is not writable. Settings saves may fail to update it.');
        return null;
    }
    if (!$allowEmpty && filesize($path) === 0) {
        shufyTheme_health_add_check($checks, 'Generated Files', 'warning', $relativePath, 'File is empty. Save its related settings page to regenerate it.');
        return null;
    }
    shufyTheme_health_add_check($checks, 'Generated Files', 'ok', $relativePath, 'File exists and is readable' . ($mustBeWritable ? '/writable.' : '.'));
}

function shufyTheme_health_table_status(array $checks, $tableName, $label, $requiresRow = false, array $requiredColumns = []) {
    if (!Manager::schema()->hasTable($tableName)) {
        shufyTheme_health_add_check($checks, 'Database', 'error', $label, 'Missing database table: ' . $tableName . '.');
        return null;
    }
    foreach ($requiredColumns as $columnName) {
        if (!Manager::schema()->hasColumn($tableName, $columnName)) {
            shufyTheme_health_add_check($checks, 'Database', 'error', $label, 'Missing required column: ' . $columnName . '.');
            return null;
        }
    }
    if ($requiresRow) {
        $hasRow = Manager::table($tableName)->where('id', 1)->exists();
        if (!$hasRow) {
            shufyTheme_health_add_check($checks, 'Database', 'warning', $label, 'Settings row with id 1 is missing. Save or reset this settings page to recreate it.');
            return null;
        }
    }
    try {
        shufyTheme_health_add_check($checks, 'Database', 'ok', $label, 'Table is available' . ($requiresRow ? ' and row id 1 exists.' : '.'));
    } catch (\Exception $e) {
        shufyTheme_health_add_check($checks, 'Database', 'error', $label, $e->getMessage());
    }
}

function shufyTheme_build_health_report($templatesCompiledir = '') {
    $checks = [];
    $addonDir = ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme';
    $cssDir = $addonDir . DIRECTORY_SEPARATOR . 'css-values';
    $backupDir = shufyTheme_settings_backup_dir();
    shufyTheme_health_add_check($checks, 'System', is_dir($addonDir) && is_readable($addonDir) ? 'ok' : 'error', 'Addon directory', is_dir($addonDir) && is_readable($addonDir) ? 'Addon directory is readable.' : 'Addon directory is missing or not readable.');
    shufyTheme_health_add_check($checks, 'System', is_dir($cssDir) && is_writable($cssDir) ? 'ok' : 'error', 'CSS values folder', is_dir($cssDir) && is_writable($cssDir) ? 'Folder is writable.' : 'Folder is missing or not writable. Generated CSS saves may fail.');
    $backupParent = dirname($backupDir);
    $backupStatus = is_dir($backupDir) ? is_writable($backupDir) : is_dir($backupParent) && is_writable($backupParent) || is_writable(dirname($backupParent));
    shufyTheme_health_add_check($checks, 'System', $backupStatus ? 'ok' : 'warning', 'Settings backup folder', $backupStatus ? 'Backup folder exists or can be created.' : 'Backup folder is not writable. Automatic backups may be skipped.');
    if ($templatesCompiledir !== '') {
        shufyTheme_health_add_check($checks, 'System', is_dir($templatesCompiledir) && is_writable($templatesCompiledir) ? 'ok' : 'warning', 'Smarty compile folder', is_dir($templatesCompiledir) && is_writable($templatesCompiledir) ? 'Smarty compile folder is writable.' : 'Smarty compile folder is missing or not writable.');
    }
    $assetFiles = [
        'assets/css/styles.css',
        'assets/js/scripts.js',
        'assets/js/jscolor.min.js',
        'assets/img/coodiv-logo.png',
    ];
    foreach ($assetFiles as $assetFile) {
        $path = $addonDir . DIRECTORY_SEPARATOR . str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $assetFile);
        shufyTheme_health_add_check($checks, 'Assets', is_file($path) && is_readable($path) ? 'ok' : 'error', $assetFile, is_file($path) && is_readable($path) ? 'Asset is available.' : 'Asset is missing or not readable.');
    }
    $settingDefinitions = shufyTheme_settings_backup_definitions();
    shufyTheme_health_table_status($checks, 'coodiv__control__panel__license', 'License table', false, ['shufythemeaddonversion']);
    shufyTheme_health_table_status($checks, 'coodiv__control__panel__table', 'Menu groups table');
    shufyTheme_health_table_status($checks, 'coodiv__control__panel_items', 'Menu items table');
    shufyTheme_health_table_status($checks, 'coodiv__control__general__settings', 'General settings', true, ['customcss_version']);
    shufyTheme_health_table_status($checks, 'coodiv__control__colors__settings', 'Colors settings', true, ['custom_colors_version']);
    shufyTheme_health_table_status($checks, 'coodiv__control__typography__settings', 'Typography settings', true);
    shufyTheme_health_table_status($checks, 'coodiv__control__layout__settings', 'Layout settings', true);
    shufyTheme_health_table_status($checks, 'coodiv__control__sidebar__settings', 'Sidebar settings', true);
    shufyTheme_health_table_status($checks, 'coodiv__control__footer__settings', 'Footer settings', true, ['accordionfootermenu']);
    shufyTheme_health_table_status($checks, 'coodiv__control__homepage__settings', 'Homepage settings', true);
    foreach ($settingDefinitions as $definition) {
        foreach ($definition['files'] as $relativePath) {
            shufyTheme_health_file_status($checks, $relativePath, true, true);
        }
    }
    $installedVersion = Manager::table('coodiv__control__panel__license')->value('shufythemeaddonversion');
    $versionStatus = $installedVersion && version_compare($installedVersion, SHUFYTHEME_ADDON_VERSION, '>=') ? 'ok' : 'warning';
    try {
        shufyTheme_health_add_check($checks, 'Version', $versionStatus, 'Addon database version', $installedVersion ? 'Database version is ' . $installedVersion . ', addon file version is ' . SHUFYTHEME_ADDON_VERSION . '.' : 'Database version is not set. Run the addon update action.');
    } catch (\Exception $e) {
        shufyTheme_health_add_check($checks, 'Version', 'error', 'Addon database version', $e->getMessage());
    }
    $groupCount = Manager::table('coodiv__control__panel__table')->count();
    shufyTheme_health_add_check($checks, 'Menus', 0 < $groupCount ? 'ok' : 'warning', 'Menu groups', 0 < $groupCount ? $groupCount . ' menu group(s) found.' : 'No menu groups found. You can create the default WHMCS menu from Menu manager.');
    $primaryCount = Manager::table('coodiv__control__panel__table')->where('isprimary', 1)->count();
    shufyTheme_health_add_check($checks, 'Menus', $primaryCount <= 1 ? ($primaryCount === 1 ? 'ok' : 'warning') : 'error', 'Primary menu assignment', $primaryCount === 1 ? 'One primary menu is active.' : ($primaryCount === 0 ? 'No primary menu is active. Native WHMCS menu may be used until one is assigned.' : $primaryCount . ' primary menus are active. Only one should be active.'));
    $footerCount = Manager::table('coodiv__control__panel__table')->where('issecondary', 1)->count();
    shufyTheme_health_add_check($checks, 'Menus', $footerCount <= 1 ? ($footerCount === 1 ? 'ok' : 'warning') : 'error', 'Footer menu assignment', $footerCount === 1 ? 'One footer menu is active.' : ($footerCount === 0 ? 'No footer menu is active.' : $footerCount . ' footer menus are active. Only one should be active.'));
    $legacyUrlCount = Manager::table('coodiv__control__panel_items')->where('urltype', 'clientarea-on')->count();
    shufyTheme_health_add_check($checks, 'Menus', $legacyUrlCount === 0 ? 'ok' : 'warning', 'Menu URL type consistency', $legacyUrlCount === 0 ? 'No legacy clientarea-on URL types found.' : $legacyUrlCount . ' menu item(s) still use legacy clientarea-on URL type. Re-save affected items or seed menus to normalize them.');
    $groupIds = [];
    $groups = Manager::table('coodiv__control__panel__table')->select('id')->get();
    foreach ($groups as $group) {
        $groupIds[] = $group->id;
    }
    $orphanQuery = Manager::table('coodiv__control__panel_items');
    if (!empty($groupIds)) {
        $orphanQuery->whereNotIn('groupid', $groupIds);
    }
    $orphanCount = $orphanQuery->count();
    try {
        shufyTheme_health_add_check($checks, 'Menus', $orphanCount === 0 ? 'ok' : 'warning', 'Orphan menu items', $orphanCount === 0 ? 'No orphan menu items found.' : $orphanCount . ' menu item(s) reference a missing group.');
    } catch (\Exception $e) {
        shufyTheme_health_add_check($checks, 'Menus', 'error', 'Menu checks', $e->getMessage());
    }
    $emailTemplateFile = $addonDir . DIRECTORY_SEPARATOR . 'extentions' . DIRECTORY_SEPARATOR . 'shufytheme-email-template' . DIRECTORY_SEPARATOR . 'shufytheme-email-template.php';
    shufyTheme_health_add_check($checks, 'Extensions', is_readable($emailTemplateFile) ? 'ok' : 'warning', 'Email template extension files', is_readable($emailTemplateFile) ? 'Email template extension files are installed.' : 'Email template extension files are not installed. This is only required if the extension is used.');
    $summary = ['ok' => 0, 'warning' => 0, 'error' => 0];
    foreach ($checks as $check) {
        ++$summary[$check['status']];
    }
    return [
        'checks' => $checks,
        'summary' => $summary,
        'generated_at' => date('Y-m-d H:i:s'),
    ];
}

function shufyTheme_settings_import_export_definitions() {
    return [
        'general' => [
            'table' => 'coodiv__control__general__settings',
            'return_action' => 'themeoption',
            'filename' => 'shufytheme_genaralsettings_exported_data.csv',
        ],
        'colors' => [
            'table' => 'coodiv__control__colors__settings',
            'return_action' => 'styleoptions',
            'filename' => 'shufytheme_styleoptions_exported_data.csv',
        ],
        'typography' => [
            'table' => 'coodiv__control__typography__settings',
            'return_action' => 'typpoptions',
            'filename' => 'shufytheme_typography_exported_data.csv',
        ],
        'layout' => [
            'table' => 'coodiv__control__layout__settings',
            'return_action' => 'layoutoptions',
            'filename' => 'shufytheme_layout_exported_data.csv',
        ],
        'sidebar' => [
            'table' => 'coodiv__control__sidebar__settings',
            'return_action' => 'sidebaroptions',
            'filename' => 'shufytheme_sidebar_exported_data.csv',
        ],
        'footer' => [
            'table' => 'coodiv__control__footer__settings',
            'return_action' => 'footeroptions',
            'filename' => 'shufytheme_footer_exported_data.csv',
        ],
        'homepage' => [
            'table' => 'coodiv__control__homepage__settings',
            'return_action' => 'homepageoptions',
            'filename' => 'shufytheme_homepage_exported_data.csv',
        ],
    ];
}

function shufyTheme_settings_import_export_action_map() {
    return [
        'exportthemeoption' => ['key' => 'general', 'type' => 'export'],
        'importthemeoption' => ['key' => 'general', 'type' => 'import'],
        'exportstyleoptions' => ['key' => 'colors', 'type' => 'export'],
        'importstyleoptions' => ['key' => 'colors', 'type' => 'import'],
        'exporttyppoptions' => ['key' => 'typography', 'type' => 'export'],
        'importtyppoptions' => ['key' => 'typography', 'type' => 'import'],
        'exportlayoutoptions' => ['key' => 'layout', 'type' => 'export'],
        'importlayoutoptions' => ['key' => 'layout', 'type' => 'import'],
        'exportsidebaroptions' => ['key' => 'sidebar', 'type' => 'export'],
        'importsidebaroptions' => ['key' => 'sidebar', 'type' => 'import'],
        'exportfooteroptions' => ['key' => 'footer', 'type' => 'export'],
        'importfooteroptions' => ['key' => 'footer', 'type' => 'import'],
        'exporthomepageptions' => ['key' => 'homepage', 'type' => 'export'],
        'importhomepageptions' => ['key' => 'homepage', 'type' => 'import'],
    ];
}

function shufyTheme_export_settings_csv(array $definition) {
    $tableName = $definition['table'];
    $columns = Manager::schema()->getColumnListing($tableName);
    $rows = Manager::table($tableName)->get();
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $definition['filename'] . '"');
    header('Pragma: no-cache');
    header('Expires: 0');
    $output = fopen('php://output', 'w');
    fwrite($output, "\xef\xbb\xbf");
    fputcsv($output, $columns);
    foreach ($rows as $row) {
        $row = (array) $row;
        $csvRow = [];
        foreach ($columns as $column) {
            $csvRow[] = array_key_exists($column, $row) ? $row[$column] : '';
        }
        fputcsv($output, $csvRow);
    }
    fclose($output);
    exit;
}

function shufyTheme_normalize_import_header(array $header) {
    if (isset($header[0])) {
        $header[0] = preg_replace('/^\\xEF\\xBB\\xBF/', '', (string) $header[0]);
    }
    return array_map(function ($column) {
        return trim((string) $column);
    }, $header);
}

function shufyTheme_is_blank_csv_row($row) {
    if (!is_array($row)) {
        return true;
    }
    foreach ($row as $value) {
        if (trim((string) $value) !== '') {
            return false;
        }
    }
    return true;
}

function shufyTheme_import_settings_csv(array $definition) {
    if (empty($_FILES['uploaded_file']) || !isset($_FILES['uploaded_file']['error'])) {
        return 'missingfile';
    }
    if ($_FILES['uploaded_file']['error'] !== UPLOAD_ERR_OK) {
        return 'uploaderror';
    }
    $tmpName = $_FILES['uploaded_file']['tmp_name'];
    if (!is_uploaded_file($tmpName) && !is_readable($tmpName)) {
        return 'uploaderror';
    }
    $handle = fopen($tmpName, 'r');
    if (!$handle) {
        return 'readerror';
    }
    $tableName = $definition['table'];
    $tableColumns = Manager::schema()->getColumnListing($tableName);
    $allowedColumns = array_flip($tableColumns);
    $header = null;
    $rows = [];
    $lineNumber = 2;
    $row = fgetcsv($handle);
    while ($row !== false) {
        ++$lineNumber;
        if (!(is_null($header) && shufyTheme_is_blank_csv_row($row))) {
            if (is_null($header)) {
                $header = shufyTheme_normalize_import_header($row);
                if (!$header || shufyTheme_is_blank_csv_row($header)) {
                    fclose($handle);
                    return 'missingheader';
                }
                foreach ($header as $columnName) {
                    if ($columnName === '' || !isset($allowedColumns[$columnName])) {
                        fclose($handle);
                        return 'invalidcolumns';
                    }
                }
            } elseif (!shufyTheme_is_blank_csv_row($row)) {
                if (count($row) !== count($header)) {
                    fclose($handle);
                    return 'invalidrow-' . $lineNumber;
                }
                $data = array_combine($header, $row);
                if (!is_array($data)) {
                    fclose($handle);
                    return 'invalidrow-' . $lineNumber;
                }
                $rows[] = $data;
            }
        }
        $row = fgetcsv($handle);
    }
    fclose($handle);
    if (is_null($header)) {
        return 'missingheader';
    }
    Manager::table($tableName)->truncate();
    try {
        foreach ($rows as $row) {
            $insertRow = [];
            foreach ($tableColumns as $columnName) {
                $insertRow[$columnName] = array_key_exists($columnName, $row) ? $row[$columnName] : '';
            }
            Manager::table($tableName)->insert($insertRow);
        }
    } catch (\Exception $e) {
        if (function_exists('logActivity')) {
        logActivity('ShufyTheme settings import failed: ' . $e->getMessage());
    }
    }
    return 'dberror';
    return 'success';
}

function shufyTheme_import_error_message($code) {
    if (strpos((string) $code, 'invalidrow-') === 0) {
        $line = substr((string) $code, 11);
        return 'The imported CSV has an invalid row length on line ' . $line . '.';
    }
    $messages = [
        'missingfile' => 'Please select a CSV file to import.',
        'uploaderror' => 'The CSV file could not be uploaded.',
        'readerror' => 'The uploaded CSV file could not be read.',
        'missingheader' => 'The CSV file is missing the header row.',
        'invalidcolumns' => 'The CSV file has invalid or unknown columns for this settings page.',
        'dberror' => 'The settings could not be imported into the database.',
    ];
    return $messages[$code] ?? 'The settings import failed.';
}

function shufyTheme_handle_settings_import_export_action($menu, $action) {
    $actions = shufyTheme_settings_import_export_action_map();
    if (!isset($actions[$action])) {
        return false;
    }
    $definitions = shufyTheme_settings_import_export_definitions();
    $definition = $definitions[$actions[$action]['key']];
    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
    if ($actions[$action]['type'] === 'export') {
        shufyTheme_export_settings_csv($definition);
    }
    try {
        $result = shufyTheme_import_settings_csv($definition);
    } catch (\Exception $e) {
        if (function_exists('logActivity')) {
        logActivity('ShufyTheme settings import/export failed: ' . $e->getMessage());
    }
    }
    $result = 'dberror';
    if ($result === 'success') {
        if ($actions[$action]['key'] === 'general') {
            shufyTheme_sync_custom_css_file_from_database();
        }
        $menu->redirect(MODURL . '&action=' . $definition['return_action'] . '&success=1');
        exit;
    }
    $menu->redirect(MODURL . '&action=' . $definition['return_action'] . '&importerror=' . urlencode($result));
    exit;
}

function shufyTheme_custom_css_file_path() {
    return ROOTDIR . DIRECTORY_SEPARATOR . 'modules' . DIRECTORY_SEPARATOR . 'addons' . DIRECTORY_SEPARATOR . 'shufyTheme' . DIRECTORY_SEPARATOR . 'css-values' . DIRECTORY_SEPARATOR . 'custom.css';
}

function shufyTheme_normalize_custom_css($css) {
    $css = (string) $css;
    $css = html_entity_decode($css, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $css = str_replace(["\r\n", "\r"], "\n", $css);
    if (substr($css, 0, 3) === "\xef\xbb\xbf") {
        $css = substr($css, 3);
    }
    return $css;
}

function shufyTheme_write_custom_css_file($css) {
    $filePath = shufyTheme_custom_css_file_path();
    $dir = dirname($filePath);
    if (!is_dir($dir)) {
        mkdir($dir, 493, true);
    }
    return file_put_contents($filePath, shufyTheme_normalize_custom_css($css), LOCK_EX) !== false;
}

function shufyTheme_sync_custom_css_file_from_database() {
    $css = Manager::table('coodiv__control__general__settings')->where('id', 1)->value('customcsscode');
    try {
        return shufyTheme_write_custom_css_file((string) $css);
    } catch (\Exception $e) {
        if (function_exists('logActivity')) {
        logActivity('ShufyTheme custom CSS sync failed: ' . $e->getMessage());
    }
    }
    return false;
}

function shufyTheme_output($vars) {
    require_once ROOTDIR . '/modules/addons/shufyTheme/classes/shufyTheme.class.php';
    define('MODURL', $vars['modulelink']);
    define('MODVERION', $vars['version']);
    global $CONFIG;
    global $templates_compiledir;
    $licenseactivated = Manager::table('coodiv__control__panel__license')->where('itemid', '52246062')->exists();
    $emailtemplatelicenseactivated = Manager::table('coodiv__control__panel__license')->where('emailtemplateextention', '61539237')->exists();
    $smarty = new Smarty();
    $smarty->setCompileDir($templates_compiledir);
    $smarty->setTemplateDir(ROOTDIR . '/modules/addons/shufyTheme/views/');
    $smarty->compile_id = md5(MODURL);
    $menu = new shufyTheme();
    $menu->displayTranslation = false;
    $_LANG = $menu->loadLanguageFile();
    $smarty->assign('_LANG', $_LANG);
    $templateFile = 'groups.tpl';
    $license__check__pages = 'license.tpl';
    $csrfToken = $vars['token'] ?? '';
    if ($csrfToken === '' && function_exists('generate_token')) {
        $csrfToken = generate_token('plain');
    }
    $smarty->assign('csrfToken', $csrfToken);
    $smarty->assign('modPageTitle', 'Shufy Theme Control Panel');
    $smarty->assign('modurl', MODURL);
    $menu->addToBreadCrumbs(MODURL, 'Shufy Theme Control Panel');
    $action = trim($_GET['action']);
    $smarty->assign('action', $action);
    if (isset($_GET['importerror'])) {
        $smarty->assign('importErrorMessage', shufyTheme_import_error_message((string) $_GET['importerror']));
    }
    $languages = $menu->getWHMCSLanguages();
    $smarty->assign('languages', $languages);
    $smarty->assign('totallanguages', count($languages));
    $menu->allAccessLevel = [
        1 => 'Always enabled',
        2 => 'Displayed for visitors only',
        3 => 'Displayed for clients only',
    ];
    $allowedActions = [
        '',
        'themeoption',
        'styleoptions',
        'typpoptions',
        'layoutoptions',
        'sidebaroptions',
        'footeroptions',
        'homepageoptions',
        'settingsbackups',
        'themehealthcheck',
        'listgroup',
        'addnewgroup',
        'listitems',
        'additem',
        'applyaddonupdate',
        'activeemailtemplate',
        'emailtemplatesettings',
        'edititem',
        'updateaddon',
        'extentions',
    ];
    if (in_array($action, $allowedActions, true)) {
        shufy_check_addon_version($smarty, $menu);
    }
    $csrfProtectedActions = [
        'sendemailtemplatelisence',
        'applyemailtemplatesettings',
        'deleteemailtemplatelisence',
        'applyaddonupdate',
        'applythemeoption',
        'resetthemeoption',
        'exportthemeoption',
        'importthemeoption',
        'resetthemecolor',
        'applythemecolor',
        'exportstyleoptions',
        'resetstyleoptions',
        'importstyleoptions',
        'applytyppoptions',
        'resettyppoptions',
        'exporttyppoptions',
        'importtyppoptions',
        'applylayoutoptions',
        'resetlayoutoptions',
        'exportlayoutoptions',
        'importlayoutoptions',
        'applysidebaroptions',
        'resetsidebaroptions',
        'exportsidebaroptions',
        'importsidebaroptions',
        'applyfooteroptions',
        'resetfooteroptions',
        'exportfooteroptions',
        'importfooteroptions',
        'applyhomepageoptions',
        'resethomepageptions',
        'exporthomepageptions',
        'importhomepageptions',
        'createsettingsbackup',
        'restoresettingsbackup',
        'deletesettingsbackup',
        'importthemeprofile',
        'lisence',
        'createdefaultwhmcsmenu',
        'createdemofootermenu',
        'applynewgroup',
        'updategroup',
        'deletegroup',
        'doadditem',
        'doedititem',
        'reorder',
        'deleteitem',
    ];
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && in_array($action, $csrfProtectedActions, true)) {
        shufyTheme_require_admin_csrf_token();
    }
    if (isset(shufyTheme_settings_backup_action_map()[$action])) {
        shufyTheme_create_settings_backup_for_action($action);
    }
    shufyTheme_handle_settings_import_export_action($menu, $action);
    if ($action == '') {
        $getGroups = Manager::table('coodiv__control__panel__license')->orderBy('id', 'desc')->get();
        $groups = $menu->fromMYSQL($getGroups);
        $smarty->assign('groups', $groups);
    } elseif ($action == 'homepage') {
        $templateFile = 'homepage.tpl';
        $getGroups = Manager::table('coodiv__control__panel__license')->orderBy('id', 'desc')->get();
        $groups = $menu->fromMYSQL($getGroups);
        $smarty->assign('groups', $groups);
    } else {
        if ($action == 'settingsbackups') {
            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
            $settingsBackups = shufyTheme_list_settings_backups();
            $backupSections = [];
            $totalBackupFiles = 2;
            foreach ($settingsBackups as $backup) {
                $backupSections[$backup['key']] = true;
                $totalBackupFiles += (int) $backup['file_count'];
            }
            $smarty->assign('backupDefinitions', shufyTheme_settings_backup_definitions());
            $smarty->assign('settingsBackups', $settingsBackups);
            $smarty->assign('backupSummary', [
                'total' => count($settingsBackups),
                'sections' => count($backupSections),
                'files' => $totalBackupFiles,
                'latest' => !empty($settingsBackups) ? $settingsBackups[0]['created_at'] : '',
            ]);
            $smarty->assign('backupDirectory', shufyTheme_settings_backup_dir());
            if (isset($_GET['profileerror'])) {
                $smarty->assign('themeProfileImportErrorMessage', shufyTheme_theme_profile_import_error_message((string) $_GET['profileerror']));
            }
            $templateFile = 'settingsbackups.tpl';
            $menu->addToBreadCrumbs('', 'Settings Backups');
        } elseif ($action == 'themehealthcheck') {
            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
            $healthReport = shufyTheme_build_health_report($templates_compiledir);
            $healthGroupsAssoc = [];
            foreach ($healthReport['checks'] as $check) {
                $healthGroupsAssoc[$check['group']][] = $check;
            }
            $healthGroups = [];
            foreach ($healthGroupsAssoc as $groupName => $checks) {
                $healthGroups[] = ['name' => $groupName, 'checks' => $checks, 'count' => count($checks)];
            }
            $totalChecks = count($healthReport['checks']);
            $overallStatus = 'ok';
            if (0 < ($healthReport['summary']['error'] ?? 0)) {
                $overallStatus = 'error';
            } elseif (0 < ($healthReport['summary']['warning'] ?? 0)) {
                $overallStatus = 'warning';
            }
            $smarty->assign('healthReport', $healthReport);
            $smarty->assign('healthGroups', $healthGroups);
            $smarty->assign('healthTotalChecks', $totalChecks);
            $smarty->assign('healthOverallStatus', $overallStatus);
            $templateFile = 'themehealthcheck.tpl';
            $menu->addToBreadCrumbs('', 'Theme Health Check');
        } else {
            if ($action == 'downloadsettingsbackup') {
                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                $file = isset($_GET['file']) ? (string) $_GET['file'] : '';
                $path = shufyTheme_settings_backup_resolve_file($file);
                if (!$path) {
                    exit('Invalid backup file.');
                }
                header('Content-Type: application/json');
                header('Content-Disposition: attachment; filename="' . basename($path) . '"');
                header('Content-Length: ' . filesize($path));
                readfile($path);
                exit;
            } elseif ($action == 'exportthemeprofile') {
                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                shufyTheme_export_theme_profile();
            } else {
                if ($action == 'importthemeprofile') {
                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                    $result = shufyTheme_import_theme_profile_from_upload();
                    $menu->redirect(MODURL . '&action=settingsbackups&' . ($result === 'success' ? 'success=profileimported' : 'error=profileimportfailed&profileerror=' . urlencode($result)));
                    exit;
                } elseif ($action == 'createsettingsbackup') {
                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                    $key = isset($_POST['backup_key']) ? (string) $_POST['backup_key'] : 'all';
                    $definitions = shufyTheme_settings_backup_definitions();
                    $created = 2;
                    if ($key === 'all') {
                        foreach (array_keys($definitions) as $definitionKey) {
                            if (shufyTheme_create_settings_backup($definitionKey, 'manual')) {
                                ++$created;
                            }
                        }
                    } elseif (isset($definitions[$key]) && shufyTheme_create_settings_backup($key, 'manual')) {
                        ++$created;
                    }
                    $menu->redirect(MODURL . '&action=settingsbackups&' . (0 < $created ? 'success=created' : 'error=backupfailed'));
                    exit;
                } else {
                    if ($action == 'restoresettingsbackup') {
                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                        $file = isset($_POST['file']) ? (string) $_POST['file'] : '';
                        $restoredKey = shufyTheme_restore_settings_backup($file);
                        $menu->redirect(MODURL . '&action=settingsbackups&' . ($restoredKey ? 'success=restored' : 'error=restorefailed'));
                        exit;
                    } elseif ($action == 'deletesettingsbackup') {
                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                        $file = isset($_POST['file']) ? (string) $_POST['file'] : '';
                        $path = shufyTheme_settings_backup_resolve_file($file);
                        if ($path) {
                            @unlink($path);
                        }
                        $menu->redirect(MODURL . '&action=settingsbackups&success=deleted');
                        exit;
                    } else {
                        if ($action == 'extentions') {
                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                            $themesettingid = 3;
                            $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                            if ($emailtemplatelicenseactivated) {
                                $smarty->assign('shufyTheme_email_template_activation', 'activated');
                            } else {
                                $smarty->assign('shufyTheme_email_template_activation', 'not-activated');
                            }
                            $templateFile = 'extentions.tpl';
                            $menu->addToBreadCrumbs('', 'ShufyTheme Extentions Manager');
                        } elseif ($action == 'activeemailtemplate') {
                            $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                            $menu->addToBreadCrumbs('', 'ShufyTheme Extentions Manager');
                            if ($emailtemplatelicenseactivated) {
                                $menu->redirect(MODURL . '&action="extentions"');
                            } else {
                                $templateFile = 'activeemailtemplate.tpl';
                            }
                        } else {
                            if ($action == 'sendemailtemplatelisence') {
                                $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                                $templateFile = 'activeemailtemplate.tpl';
                                if ($emailtemplatelicenseactivated) {
                                    $menu->redirect(MODURL . '&action=extentions&success=1');
                                } elseif (function_exists('shufyTheme_email_template_active')) {
                                    shufyTheme_email_template_active();
                                    if (isset($_POST['purchase_code'])) {
                                        $purchase_code = htmlspecialchars($_POST['purchase_code']);
                                        $emailtempltepurchase = EnvatoApi2::verifyPurchase($purchase_code);
                                        if (is_object($emailtempltepurchase)) {
                                            Manager::table('coodiv__control__panel__license')->update(['emailtemplateextention' => (string) $emailtempltepurchase->item->id]);
                                            $menu->redirect(MODURL . '&action=extentions&success=1');
                                            goto label_683;
                                            $menu->redirect(MODURL . '&action=activeemailtemplate&error=1');
                                        } else {
                                            label_683:
                                            $menu->redirect(MODURL . '&action=activeemailtemplate&error=2');
                                        }
                                    }
                                } else {
                                    $menu->redirect(MODURL . '&action=activeemailtemplate&error=4');
                                }
                            } elseif ($action == 'emailtemplatesettings') {
                                $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                                $themesettingid = '1';
                                $smarty->assign('themesettingid', $themesettingid);
                                $menu->addToBreadCrumbs('', 'ShufyTheme Email template settings');
                                if ($emailtemplatelicenseactivated) {
                                    $templateFile = 'emailtemplatesettings.tpl';
                                    $getItemInfo = Manager::table('coodiv__email__template__settings')->where('id', $themesettingid)->get();
                                    $emailtemplatesettings = $menu->fromMYSQL($getItemInfo);
                                    $smarty->assign('emailtemplatesettings', $emailtemplatesettings[0] ?? []);
                                } else {
                                    $menu->redirect(MODURL . '&action=extentions&error=3');
                                }
                            } else {
                                if ($action == 'applyemailtemplatesettings') {
                                    $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                                    if ($emailtemplatelicenseactivated) {
                                        $templateFile = 'settingssavingloader.tpl';
                                        if (function_exists('shufyTheme_update_email_css') && function_exists('shufyTheme_update_email_header') && function_exists('shufyTheme_update_email_footer')) {
                                            $emailTheme = (string) $menu->input($_POST['emailtemplatetheme']);
                                            $emailtemplatedata = [
                                                'logo' => $menu->input($_POST['emailtemplatelogolinklight']),
                                                'header_text' => $menu->input($_POST['emailtemplateheadertext']),
                                                'header_subtext' => $menu->input($_POST['emailtemplateheaderlinktext']),
                                                'header_link' => $menu->input($_POST['emailtemplateheaderlink']),
                                                'copyright' => $menu->input($_POST['emailtemplatecopyrighttext']),
                                                'domain' => $menu->input($_POST['emailtemplatedomainlinkfooter']),
                                                'facebook' => $menu->input($_POST['emailtemplatefacebooklink']),
                                                'twitter' => $menu->input($_POST['emailtemplatetwitterlink']),
                                                'linkedin' => $menu->input($_POST['emailtemplatelinkedinlink']),
                                                'instagram' => $menu->input($_POST['emailtemplateinstagramlink']),
                                                'whatsapp' => $menu->input($_POST['emailtemplateyoutubelink']),
                                                'linkone' => $menu->input($_POST['emailtemplatefooterlinkone']),
                                                'linkoneurl' => $menu->input($_POST['emailtemplatefooterlinkoneurl']),
                                                'linktwo' => $menu->input($_POST['emailtemplatefooterlinktwo']),
                                                'linktwourl' => $menu->input($_POST['emailtemplatefooterlinktwourl']),
                                                'linkthree' => $menu->input($_POST['emailtemplatefooterlinkthree']),
                                                'linkthreeurl' => $menu->input($_POST['emailtemplatefooterlinkthreeurl']),
                                                'linkfour' => $menu->input($_POST['emailtemplatefooterlinktfour']),
                                                'linkfoururl' => $menu->input($_POST['emailtemplatefooterlinktfoururl']),
                                                'footertext' => $menu->input($_POST['emailtemplateheadertext']),
                                                'footerlinktext' => $menu->input($_POST['emailtemplateheaderlinktext']),
                                                'footerlinkurl' => $menu->input($_POST['emailtemplateheaderlink']),
                                                'emailtemplatecopyrighttext' => $menu->input($_POST['emailtemplatecopyrighttext']),
                                            ];
                                            Manager::statement('TRUNCATE TABLE coodiv__email__template__settings');
                                            Manager::table('coodiv__email__template__settings')->insert([
                                                'emailtemplatelogolinklight' => (string) $menu->input($_POST['emailtemplatelogolinklight']),
                                                'emailtemplatelogolinkdark' => (string) $menu->input($_POST['emailtemplatelogolinkdark']),
                                                'emailtemplateheadertext' => (string) $menu->input($_POST['emailtemplateheadertext']),
                                                'emailtemplateheaderlinktext' => (string) $menu->input($_POST['emailtemplateheaderlinktext']),
                                                'emailtemplateheaderlink' => (string) $menu->input($_POST['emailtemplateheaderlink']),
                                                'emailtemplatedomainlinkfooter' => (string) $menu->input($_POST['emailtemplatedomainlinkfooter']),
                                                'emailtemplatefacebooklink' => (string) $menu->input($_POST['emailtemplatefacebooklink']),
                                                'emailtemplatetwitterlink' => (string) $menu->input($_POST['emailtemplatetwitterlink']),
                                                'emailtemplatelinkedinlink' => (string) $menu->input($_POST['emailtemplatelinkedinlink']),
                                                'emailtemplateyoutubelink' => (string) $menu->input($_POST['emailtemplateyoutubelink']),
                                                'emailtemplateinstagramlink' => (string) $menu->input($_POST['emailtemplateinstagramlink']),
                                                'emailtemplatecopyrighttext' => (string) $menu->input($_POST['emailtemplatecopyrighttext']),
                                                'emailtemplatefooterlinkone' => (string) $menu->input($_POST['emailtemplatefooterlinkone']),
                                                'emailtemplatefooterlinkoneurl' => (string) $menu->input($_POST['emailtemplatefooterlinkoneurl']),
                                                'emailtemplatefooterlinktwo' => (string) $menu->input($_POST['emailtemplatefooterlinktwo']),
                                                'emailtemplatefooterlinktwourl' => (string) $menu->input($_POST['emailtemplatefooterlinktwourl']),
                                                'emailtemplatefooterlinkthree' => (string) $menu->input($_POST['emailtemplatefooterlinkthree']),
                                                'emailtemplatefooterlinkthreeurl' => (string) $menu->input($_POST['emailtemplatefooterlinkthreeurl']),
                                                'emailtemplatefooterlinktfour' => (string) $menu->input($_POST['emailtemplatefooterlinktfour']),
                                                'emailtemplatefooterlinktfoururl' => (string) $menu->input($_POST['emailtemplatefooterlinktfoururl']),
                                                'emailtemplatetheme' => (string) $menu->input($_POST['emailtemplatetheme']),
                                            ]);
                                            shufyTheme_update_email_css($emailTheme);
                                            shufyTheme_update_email_header($emailtemplatedata, $emailTheme);
                                            shufyTheme_update_email_footer($emailtemplatedata, $emailTheme);
                                            $menu->redirect(MODURL . '&action=emailtemplatesettings&success=1');
                                            exit;
                                            goto label_1139;
                                            $menu->redirect(MODURL . '&action=emailtemplatesettings&error=1');
                                            exit;
                                        } else {
                                            label_1139:
                                            $menu->redirect(MODURL . '&action=emailtemplatesettings&error=extensionfileerror');
                                        }
                                    } else {
                                        $menu->redirect(MODURL . '&action=extentions&error=3');
                                    }
                                } elseif ($action == 'deleteemailtemplatelisence') {
                                    $smarty->assign('shufyTheme_email_template', shufyTheme_email_template_status());
                                    if ($emailtemplatelicenseactivated) {
                                        if (function_exists('shufyTheme_email_template_deactive')) {
                                            shufyTheme_email_template_deactive();
                                        }
                                        Manager::table('coodiv__control__panel__license')->update(['emailtemplateextention' => 'empty']);
                                        $menu->redirect(MODURL . '&action=extentions&success=2');
                                        try {
                                            exit;
                                        } catch (\Exception $e) {
                                            exit('Error: ' . $e->getMessage());
                                        }
                                    }
                                } else {
                                    if ($action == 'updateaddon') {
                                        $smarty->assign('updateSuccess', isset($_GET['success']));
                                        $smarty->assign('updateErrorFlag', isset($_GET['error']));
                                        $smarty->assign('updateErrorFlagtext', isset($_GET['updateError']));
                                        $templateFile = 'updateaddon.tpl';
                                        $menu->addToBreadCrumbs('', 'Shufy Theme General Settings');
                                    } elseif ($action == 'applyaddonupdate') {
                                        $templateFile = 'applyaddonupdateloader.tpl';
                                        $menu->addToBreadCrumbs('', 'ShufyTheme update');
                                        $result = updateshufythemeaddon();
                                        if ($result !== true) {
                                            $smarty->assign('updateError', $result);
                                        } else {
                                            $smarty->assign('updateSuccess', true);
                                        }
                                    } else {
                                        if ($action == 'themeoption') {
                                            $themesettingid = '1';
                                            $smarty->assign('themesettingid', $themesettingid);
                                            $getItemInfo = Manager::table('coodiv__control__general__settings')->where('id', $themesettingid)->get();
                                            $themesetting = $menu->fromMYSQL($getItemInfo);
                                            $smarty->assign('themesetting', $themesetting[0] ?? []);
                                            $templateFile = 'themeoption.tpl';
                                            $menu->addToBreadCrumbs('', 'Shufy Theme Genaral settings');
                                        } elseif ($action == 'applythemeoption') {
                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                            $customCssCode = shufyTheme_normalize_custom_css($_POST['customcsscode'] ?? '');
                                            $customCssWriteOk = true;
                                            if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                $customCssWriteOk = shufyTheme_write_custom_css_file($customCssCode);
                                            }
                                            $currentVersion = Manager::table('coodiv__control__general__settings')->value('customcss_version');
                                            $currentVersion = $currentVersion ?: '1.0.0';
                                            $newVersion = shufy_increment_version($currentVersion);
                                            if (!$customCssWriteOk) {
                                                throw new Exception('Custom CSS file is not writable.');
                                            }
                                            Manager::statement('TRUNCATE TABLE coodiv__control__general__settings');
                                            $groupid = Manager::table('coodiv__control__general__settings')->insertGetId([
                                                'siteaslogo' => (string) $menu->input($_POST['textlogo']),
                                                'customtextlogo' => (string) $menu->input($_POST['customtextlogo']),
                                                'customcss_version' => $newVersion,
                                                'defaultlogolinkicon' => (string) $menu->input($_POST['defaultlogolinkicon']),
                                                'defaultlogolinktagline' => (string) $menu->input($_POST['defaultlogolinktagline']),
                                                'defaultlogolinkfull' => (string) $menu->input($_POST['defaultlogolinkfull']),
                                                'darklogolinkicon' => (string) $menu->input($_POST['darklogolinkicon']),
                                                'darklogolinktagline' => (string) $menu->input($_POST['darklogolinktagline']),
                                                'darklogolinkfull' => (string) $menu->input($_POST['darklogolinkfull']),
                                                'advancedemailverification' => (string) $menu->input($_POST['advancedemailverification']),
                                                'customerspin' => (string) $menu->input($_POST['customerspin']),
                                                'customersnotifications' => (string) $menu->input($_POST['customersnotifications']),
                                                'gravatar' => (string) $menu->input($_POST['gravatar']),
                                                'headeranoncement' => (string) $menu->input($_POST['h-anoncement']),
                                                'userdropdown' => (string) $menu->input($_POST['user-dropdown']),
                                                'notificationdropdown' => (string) $menu->input($_POST['notification-dropdown']),
                                                'cartdropdown' => (string) $menu->input($_POST['cart-dropdown']),
                                                'clientmarketconnect' => (string) $menu->input($_POST['client-marketconnect']),
                                                'servicemarketconnect' => (string) $menu->input($_POST['services-marketconnect']),
                                                'domainmarketconnect' => (string) $menu->input($_POST['domains-marketconnect']),
                                                'loginstyle' => (string) $menu->input($_POST['login-style']),
                                                'registerstyle' => (string) $menu->input($_POST['register-style']),
                                                'cookiesbox' => (string) $menu->input($_POST['cookiesbox']),
                                                'cookiesboxposition' => (string) $menu->input($_POST['cookiesboxposition']),
                                                'cookiesboxtext' => (string) $menu->input($_POST['cookiesboxtext']),
                                                'seositename' => (string) $menu->input($_POST['seostitename']),
                                                'seositedescription' => (string) $menu->input($_POST['seositedesc']),
                                                'seositefavicon' => (string) $menu->input($_POST['seositefavicon']),
                                                'seoorganizationname' => (string) $menu->input($_POST['seoorgname']),
                                                'seoorganizationphonenumber' => (string) $menu->input($_POST['eoorgmobile']),
                                                'seoopengraph' => (string) $menu->input($_POST['seoopengraph']),
                                                'seoalternatewebsitename' => (string) $menu->input($_POST['seoaltername']),
                                                'seowebsitetype' => (string) $menu->input($_POST['seowtype']),
                                                'seocontacttype' => (string) $menu->input($_POST['seocontacttype']),
                                                'seotwitterusername' => (string) $menu->input($_POST['seotwittername']),
                                                'customcsscode' => $customCssCode,
                                                'headerlanguage' => (string) $menu->input($_POST['headerlanguage']),
                                                'footerlanguagelanguage' => (string) $menu->input($_POST['footerlanguagelanguage']),
                                                'registerformlanguage' => (string) $menu->input($_POST['registerformlanguage']),
                                                'loginformlanguage' => (string) $menu->input($_POST['loginformlanguage']),
                                                'allowproductsliderswitch' => (string) $menu->input($_POST['allowproductsliderswitch']),
                                                'productasslider' => (string) $menu->input($_POST['productasslider']),
                                                'additionelsetting' => (string) $menu->input($_POST['additionelsetting']),
                                                'accountoverview' => (string) $menu->input($_POST['accountoverview']),
                                                'clientareamaininformations' => (string) $menu->input($_POST['clientareamaininformations']),
                                                'clientareaservices' => (string) $menu->input($_POST['clientareaservices']),
                                                'clientareatickets' => (string) $menu->input($_POST['clientareatickets']),
                                                'clientareadomains' => (string) $menu->input($_POST['clientareadomains']),
                                                'clientareaannouncements' => (string) $menu->input($_POST['clientareaannouncements']),
                                                'customthemeloader' => (string) $menu->input($_POST['customthemeloader']),
                                                'cookiesbox_header' => (string) $menu->input($_POST['cookiesbox_header']),
                                                'cookiesbox_link_text' => (string) $menu->input($_POST['cookiesbox_link_text']),
                                                'cookiesbox_link_url' => (string) $menu->input($_POST['cookiesbox_link_url']),
                                            ]);
                                            try {
                                                shufyTheme_ajax_or_redirect($menu, MODURL . '&action=themeoption&success=1', [
                                                    'message' => 'Shufytheme Genaral settings options has been saved successfully.',
                                                    'customcss_version' => $newVersion,
                                                ]);
                                            } catch (\Exception $e) {
                                                exit('Error: ' . $e->getMessage());
                                            }
                                        } else {
                                            if ($action == 'resetthemeoption') {
                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                $tableName = 'coodiv__control__general__settings';
                                                $columns = Manager::schema()->getColumnListing($tableName);
                                                $updateData = array_fill_keys($columns, '');
                                                Manager::table($tableName)->update($updateData);
                                                shufyTheme_write_custom_css_file('');
                                                $menu->redirect(MODURL . '&action=themeoption&genaralsettingsreset=1');
                                                try {
                                                    exit;
                                                } catch (\Exception $e) {
                                                    exit('Error: ' . $e->getMessage());
                                                }
                                            } else {
                                                if ($action == 'exportthemeoption') {
                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                    $themeOptionData = Manager::table('coodiv__control__general__settings')->get();
                                                    $csvData = [];
                                                    $csvData[] = array_keys((array) $themeOptionData->first());
                                                    foreach ($themeOptionData as $row) {
                                                        $csvData[] = (array) $row;
                                                    }
                                                    $csvContent = implode("\n", array_map(function ($version) {
                                                        $parts = explode('.', $version);
                                                        while (count($parts) < 3) {
                                                            $parts[] = 0;
                                                        }
                                                        $parts[2] = (int) $parts[2] + 1;
                                                        return implode('.', $parts);
                                                    }, $csvData));
                                                    header('Content-Type: text/csv');
                                                    header('Content-Disposition: attachment; filename="shufytheme_genaralsettings_exported_data.csv"');
                                                    echo $csvContent;
                                                    try {
                                                        exit;
                                                    } catch (\Exception $e) {
                                                        exit('Error: ' . $e->getMessage());
                                                    }
                                                } else {
                                                    if ($action == 'importthemeoption') {
                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                        if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                            $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                            $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                            $columns = array_shift($csvData);
                                                            $validData = true;
                                                            $invalidRow = null;
                                                            foreach ($csvData as $index => $row) {
                                                                if (count($row) !== count($columns)) {
                                                                    $validData = false;
                                                                    $invalidRow = $index + 1;
                                                                    break;
                                                                }
                                                            }
                                                            if ($validData) {
                                                                Manager::table('coodiv__control__general__settings')->truncate();
                                                                foreach ($csvData as $row) {
                                                                    $data = array_combine($columns, $row);
                                                                    Manager::table('coodiv__control__general__settings')->insert($data);
                                                                }
                                                                echo 'Upload successful! Data has been overwritten.';
                                                                $menu->redirect(MODURL . '&action=themeoption&success=1');
                                                                exit;
                                                            } else {
                                                                echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                            }
                                                        } else {
                                                            echo 'Error uploading file.';
                                                        }
                                                        try {
                                                            exit;
                                                        } catch (\Exception $e) {
                                                            exit('Error: ' . $e->getMessage());
                                                        }
                                                    } else {
                                                        if ($action == 'styleoptions') {
                                                            $themesettingid = '1';
                                                            $smarty->assign('themesettingid', $themesettingid);
                                                            $getItemInfo = Manager::table('coodiv__control__colors__settings')->where('id', $themesettingid)->get();
                                                            $themesetting = $menu->fromMYSQL($getItemInfo);
                                                            $smarty->assign('themecolorsetting', $themesetting[0] ?? []);
                                                            $templateFile = 'styleoptions.tpl';
                                                            $menu->addToBreadCrumbs('', 'Shufy Theme Styles & colors settings');
                                                        } elseif ($action == 'resetthemecolor') {
                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                            Manager::statement('TRUNCATE TABLE coodiv__control__colors__settings');
                                                            $menu->redirect(MODURL . '&action=styleoptions&success=1');
                                                            try {
                                                                exit;
                                                            } catch (\Exception $e) {
                                                                exit('Error: ' . $e->getMessage());
                                                            }
                                                        } else {
                                                            if ($action == 'applythemecolor') {
                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                    $data1 = $_POST['backroundone'];
                                                                    $data2 = $_POST['backroundtwo'];
                                                                    $data3 = $_POST['backroundtree'];
                                                                    $data4 = $_POST['backroundfour'];
                                                                    $data5 = $_POST['backroundfive'];
                                                                    $data6 = $_POST['backroundsix'];
                                                                    $data7 = $_POST['backroundsaven'];
                                                                    $data8 = $_POST['backroundeight'];
                                                                    $data9 = $_POST['backroundnine'];
                                                                    $data10 = $_POST['backroundten'];
                                                                    $data11 = $_POST['backroundeleven'];
                                                                    $data12 = $_POST['backroundtwelve'];
                                                                    $data13 = $_POST['backroundthirteen'];
                                                                    $data14 = $_POST['backroundfourteen'];
                                                                    $data15 = $_POST['backroundfifteen'];
                                                                    $data16 = $_POST['btnprimarybg'];
                                                                    $data17 = $_POST['btnprimaryborder'];
                                                                    $data18 = $_POST['btnprimarycolor'];
                                                                    $data19 = $_POST['btnprimarybghover'];
                                                                    $data20 = $_POST['btnprimaryborderhover'];
                                                                    $data21 = $_POST['btnprimarycolorhover'];
                                                                    $data22 = $_POST['btnprimarylightbg'];
                                                                    $data23 = $_POST['btnprimarylightborder'];
                                                                    $data24 = $_POST['btnprimarylightcolor'];
                                                                    $data25 = $_POST['btnprimarylightbghover'];
                                                                    $data26 = $_POST['btnprimarylightborderhover'];
                                                                    $data27 = $_POST['btnprimarylightcolorhover'];
                                                                    $data28 = $_POST['btndefaultbg'];
                                                                    $data29 = $_POST['btndefaultborder'];
                                                                    $data30 = $_POST['btndefaultcolor'];
                                                                    $data31 = $_POST['btndefaultbghover'];
                                                                    $data32 = $_POST['btndefaultborderhover'];
                                                                    $data33 = $_POST['btndefaultcolorhover'];
                                                                    $data34 = $_POST['btnprimaryoutlinebg'];
                                                                    $data35 = $_POST['btnprimaryoutlineborder'];
                                                                    $data36 = $_POST['btnprimaryoutlinecolor'];
                                                                    $data37 = $_POST['btnprimaryoutlinebghover'];
                                                                    $data38 = $_POST['btnprimaryoutlineborderhover'];
                                                                    $data39 = $_POST['btnprimaryoutlinecolorhover'];
                                                                    $data40 = $_POST['btnprimaryoutlinewhitebg'];
                                                                    $data41 = $_POST['btnprimaryoutlinewhiteborder'];
                                                                    $data42 = $_POST['btnprimaryoutlinewhitecolor'];
                                                                    $data43 = $_POST['btnprimaryoutlinewhitebghover'];
                                                                    $data44 = $_POST['btnprimaryoutlinewhiteborderhover'];
                                                                    $data45 = $_POST['btnprimaryoutlinewhitecolorhover'];
                                                                    $data46 = $_POST['btnprimaryoutlinelightbg'];
                                                                    $data47 = $_POST['btnprimaryoutlinelightborder'];
                                                                    $data48 = $_POST['btnprimaryoutlinelightcolor'];
                                                                    $data49 = $_POST['btnprimaryoutlinelightbghover'];
                                                                    $data50 = $_POST['btnprimaryoutlinelightborderhover'];
                                                                    $data51 = $_POST['btnprimaryoutlinelightcolorhover'];
                                                                    $data52 = $_POST['textstagscoloroneheading'];
                                                                    $data53 = $_POST['textstagscoloroneheadinghover'];
                                                                    $data54 = $_POST['textstagscoloroneheadinggray'];
                                                                    $data55 = $_POST['textstagscoloronesubheading'];
                                                                    $data56 = $_POST['textstagscoloronetextcolor'];
                                                                    $data57 = $_POST['textstagscoloronetextcoloropacity'];
                                                                    $data58 = $_POST['textstagscoloroneborder'];
                                                                    $data59 = $_POST['textstagscoloroneborderlight'];
                                                                    $data60 = $_POST['textstagscoloronelink'];
                                                                    $data61 = $_POST['textstagscoloronelinkhover'];
                                                                    $data62 = $_POST['sidebarcolorsdefaultonebg'];
                                                                    $data63 = $_POST['sidebarcolorsdefaultoneextendbtnbg'];
                                                                    $data64 = $_POST['sidebarcolorsdefaultoneitembg'];
                                                                    $data65 = $_POST['sidebarcolorsdefaultoneitemhoverbg'];
                                                                    $data66 = $_POST['sidebarcolorsdefaultoneitemtext'];
                                                                    $data67 = $_POST['sidebarcolorsdefaultoneitemicon'];
                                                                    $data68 = $_POST['sidebarcolorsdefaultoneitemtexthover'];
                                                                    $data69 = $_POST['sidebarcolorsdefaultoneitemiconhover'];
                                                                    $data70 = $_POST['sidebarcolorsdefaultonedropdownbg'];
                                                                    $data71 = $_POST['sidebarcolorsdefaultonedropdowntitle'];
                                                                    $data72 = $_POST['sidebarcolorsdefaultonedropdownitembg'];
                                                                    $data73 = $_POST['sidebarcolorsdefaultonedropdownitemtext'];
                                                                    $data74 = $_POST['sidebarcolorsdefaultonedropdownitemicon'];
                                                                    $data75 = $_POST['sidebarcolorsdefaultonedropdownitemtexthover'];
                                                                    $data76 = $_POST['sidebarcolorsdefaultonedropdownitemiconhover'];
                                                                    $data77 = $_POST['sidebarcolorsdarkonebg'];
                                                                    $data78 = $_POST['sidebarcolorsdarkoneextendbtnbg'];
                                                                    $data79 = $_POST['sidebarcolorsdarkoneitembg'];
                                                                    $data80 = $_POST['sidebarcolorsdarkoneitemhoverbg'];
                                                                    $data81 = $_POST['sidebarcolorsdarkoneitemtext'];
                                                                    $data82 = $_POST['sidebarcolorsdarkoneitemicon'];
                                                                    $data83 = $_POST['sidebarcolorsdarkoneitemtexthover'];
                                                                    $data84 = $_POST['sidebarcolorsdarkoneitemiconhover'];
                                                                    $data85 = $_POST['sidebarcolorsdarkonedropdownbg'];
                                                                    $data86 = $_POST['sidebarcolorsdarkonedropdowntitle'];
                                                                    $data87 = $_POST['sidebarcolorsdarkonedropdownitembg'];
                                                                    $data88 = $_POST['sidebarcolorsdarkonedropdownitemtext'];
                                                                    $data89 = $_POST['sidebarcolorsdarkonedropdownitemicon'];
                                                                    $data90 = $_POST['sidebarcolorsdarkonedropdownitemtexthover'];
                                                                    $data91 = $_POST['sidebarcolorsdarkonedropdownitemiconhover'];
                                                                    $data92 = $_POST['alertbgprimary'];
                                                                    $data93 = $_POST['alertcolorprimary'];
                                                                    $data94 = $_POST['alertbgsecondary'];
                                                                    $data95 = $_POST['alertcolorsecondary'];
                                                                    $data96 = $_POST['alertbgsuccess'];
                                                                    $data97 = $_POST['alertcolorsuccess'];
                                                                    $data98 = $_POST['alertbgdanger'];
                                                                    $data99 = $_POST['alertcolordanger'];
                                                                    $data100 = $_POST['alertbgwarning'];
                                                                    $data101 = $_POST['alertcolorwarning'];
                                                                    $data102 = $_POST['alertbginfo'];
                                                                    $data103 = $_POST['alertcolorinfo'];
                                                                    $data104 = $_POST['alertbglight'];
                                                                    $data105 = $_POST['alertcolorlight'];
                                                                    $data106 = $_POST['alertbgdark'];
                                                                    $data107 = $_POST['alertcolordark'];
                                                                    $data108 = $_POST['btnlightbg'];
                                                                    $data109 = $_POST['btnlightborder'];
                                                                    $data110 = $_POST['btnlightcolor'];
                                                                    $data111 = $_POST['btnlightbghover'];
                                                                    $data112 = $_POST['btnlightborderhover'];
                                                                    $data113 = $_POST['btnlightcolorhover'];
                                                                    $data114 = $_POST['btnlighterbg'];
                                                                    $data115 = $_POST['btnlighterborder'];
                                                                    $data116 = $_POST['btnlightercolor'];
                                                                    $data117 = $_POST['btnlighterbghover'];
                                                                    $data118 = $_POST['btnlighterborderhover'];
                                                                    $data119 = $_POST['btnlightercolorhover'];
                                                                    $header = 'body{';
                                                                    $footer = '}';
                                                                    $titles = [
                                                                        '--background',
                                                                        '--background-2',
                                                                        '--background-3',
                                                                        '--background-4',
                                                                        '--background-5',
                                                                        '--background-6',
                                                                        '--background-7',
                                                                        '--background-8',
                                                                        '--background-9',
                                                                        '--background-10',
                                                                        '--background-11',
                                                                        '--background-12',
                                                                        '--background-13',
                                                                        '--background-14',
                                                                        '--background-15',
                                                                        '--btn-primary-bg',
                                                                        '--btn-primary-border',
                                                                        '--btn-primary-color',
                                                                        '--btn-primary-bg-hover',
                                                                        '--btn-primary-border-hover',
                                                                        '--btn-primary-color-hover',
                                                                        '--btn-primary-light-bg',
                                                                        '--btn-primary-light-border',
                                                                        '--btn-primary-light-color',
                                                                        '--btn-primary-light-bg-hover',
                                                                        '--btn-primary-light-border-hover',
                                                                        '--btn-primary-light-color-hover',
                                                                        '--btn-default-bg',
                                                                        '--btn-default-border',
                                                                        '--btn-default-color',
                                                                        '--btn-default-bg-hover',
                                                                        '--btn-default-border-hover',
                                                                        '--btn-default-color-hover',
                                                                        '--btn-primary-outlin-bg',
                                                                        '--btn-primary-outlin-border',
                                                                        '--btn-primary-outlin-color',
                                                                        '--btn-primary-outlin-bg-hover',
                                                                        '--btn-primary-outlin-border-hover',
                                                                        '--btn-primary-outlin-color-hover',
                                                                        '--btn-primary-outlin-white-bg',
                                                                        '--btn-primary-outlin-white-border',
                                                                        '--btn-primary-outlin-white-color',
                                                                        '--btn-primary-outlin-white-bg-hover',
                                                                        '--btn-primary-outlin-white-border-hover',
                                                                        '--btn-primary-outlin-white-color-hover',
                                                                        '--btn-primary-outlin-light-bg',
                                                                        '--btn-primary-outlin-light-border',
                                                                        '--btn-primary-outlin-light-color',
                                                                        '--btn-primary-outlin-light-bg-hover',
                                                                        '--btn-primary-outlin-light-border-hover',
                                                                        '--btn-primary-outlin-light-color-hover',
                                                                        '--color-h',
                                                                        '--color-h-hover',
                                                                        '--color-gray',
                                                                        '--color-h-sub',
                                                                        '--color-texts',
                                                                        '--color-texts-opacity',
                                                                        '--border-color',
                                                                        '--border-color-light',
                                                                        '--a-link-color',
                                                                        '--a-link-color-hover',
                                                                        '--sidebarcolorsdefaultonebg',
                                                                        '--sidebarcolorsdefaultoneextendbtnbg',
                                                                        '--sidebarcolorsdefaultoneitembg',
                                                                        '--sidebarcolorsdefaultoneitemhoverbg',
                                                                        '--sidebarcolorsdefaultoneitemtext',
                                                                        '--sidebarcolorsdefaultoneitemicon',
                                                                        '--sidebarcolorsdefaultoneitemtexthover',
                                                                        '--sidebarcolorsdefaultoneitemiconhover',
                                                                        '--sidebarcolorsdefaultonedropdownbg',
                                                                        '--sidebarcolorsdefaultonedropdowntitle',
                                                                        '--sidebarcolorsdefaultonedropdownitembg',
                                                                        '--sidebarcolorsdefaultonedropdownitemtext',
                                                                        '--sidebarcolorsdefaultonedropdownitemicon',
                                                                        '--sidebarcolorsdefaultonedropdownitemtexthover',
                                                                        '--sidebarcolorsdefaultonedropdownitemiconhover',
                                                                        '--sidebarcolorsdarkonebg',
                                                                        '--sidebarcolorsdarkoneextendbtnbg',
                                                                        '--sidebarcolorsdarkoneitembg',
                                                                        '--sidebarcolorsdarkoneitemhoverbg',
                                                                        '--sidebarcolorsdarkoneitemtext',
                                                                        '--sidebarcolorsdarkoneitemicon',
                                                                        '--sidebarcolorsdarkoneitemtexthover',
                                                                        '--sidebarcolorsdarkoneitemiconhover',
                                                                        '--sidebarcolorsdarkonedropdownbg',
                                                                        '--sidebarcolorsdarkonedropdowntitle',
                                                                        '--sidebarcolorsdarkonedropdownitembg',
                                                                        '--sidebarcolorsdarkonedropdownitemtext',
                                                                        '--sidebarcolorsdarkonedropdownitemicon',
                                                                        '--sidebarcolorsdarkonedropdownitemtexthover',
                                                                        '--sidebarcolorsdarkonedropdownitemiconhover',
                                                                        '--alertbgprimary',
                                                                        '--alertcolorprimary',
                                                                        '--alertbgsecondary',
                                                                        '--alertcolorsecondary',
                                                                        '--alertbgsuccess',
                                                                        '--alertcolorsuccess',
                                                                        '--alertbgdanger',
                                                                        '--alertcolordanger',
                                                                        '--alertbgwarning',
                                                                        '--alertcolorwarning',
                                                                        '--alertbginfo',
                                                                        '--alertcolorinfo',
                                                                        '--alertbglight',
                                                                        '--alertcolorlight',
                                                                        '--alertbgdark',
                                                                        '--alertcolordark',
                                                                        '--btn-light-bg',
                                                                        '--btn-light-border',
                                                                        '--btn-light-color',
                                                                        '--btn-light-bg-hover',
                                                                        '--btn-light-border-hover',
                                                                        '--btn-light-color-hover',
                                                                        '--btn-lighter-bg',
                                                                        '--btn-lighter-border',
                                                                        '--btn-lighter-color',
                                                                        '--btn-lighter-bg-hover',
                                                                        '--btn-lighter-border-hover',
                                                                        '--btn-lighter-color-hover',
                                                                    ];
                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/default-style.css';
                                                                    $file = fopen($filePath, 'w');
                                                                    fwrite($file, $header . PHP_EOL);
                                                                    $i = 2;
                                                                    while ($i < count($titles)) {
                                                                        fwrite($file, $titles[$i] . ': ' . ${'data' . $i + 1} . ';');
                                                                        ++$i;
                                                                    }
                                                                    fwrite($file, $footer . PHP_EOL);
                                                                    fclose($file);
                                                                }
                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                    $data1 = $_POST['backroundonetwo'];
                                                                    $data2 = $_POST['backroundtwotwo'];
                                                                    $data3 = $_POST['backroundtreetwo'];
                                                                    $data4 = $_POST['backroundfourtwo'];
                                                                    $data5 = $_POST['backroundfivetwo'];
                                                                    $data6 = $_POST['backroundsixtwo'];
                                                                    $data7 = $_POST['backroundsaventwo'];
                                                                    $data8 = $_POST['backroundeighttwo'];
                                                                    $data9 = $_POST['backroundninetwo'];
                                                                    $data10 = $_POST['backroundtentwo'];
                                                                    $data11 = $_POST['backroundeleventwo'];
                                                                    $data12 = $_POST['backroundtwelvetwo'];
                                                                    $data13 = $_POST['backroundthirteentwo'];
                                                                    $data14 = $_POST['backroundfourteentwo'];
                                                                    $data15 = $_POST['backroundfifteentwo'];
                                                                    $data16 = $_POST['btnprimarybgtwo'];
                                                                    $data17 = $_POST['btnprimarybordertwo'];
                                                                    $data18 = $_POST['btnprimarycolortwo'];
                                                                    $data19 = $_POST['btnprimarybghovertwo'];
                                                                    $data20 = $_POST['btnprimaryborderhovertwo'];
                                                                    $data21 = $_POST['btnprimarycolorhovertwo'];
                                                                    $data22 = $_POST['btnprimarylightbgtwo'];
                                                                    $data23 = $_POST['btnprimarylightbordertwo'];
                                                                    $data24 = $_POST['btnprimarylightcolortwo'];
                                                                    $data25 = $_POST['btnprimarylightbghovertwo'];
                                                                    $data26 = $_POST['btnprimarylightborderhovertwo'];
                                                                    $data27 = $_POST['btnprimarylightcolorhovertwo'];
                                                                    $data28 = $_POST['btndefaultbgtwo'];
                                                                    $data29 = $_POST['btndefaultbordertwo'];
                                                                    $data30 = $_POST['btndefaultcolortwo'];
                                                                    $data31 = $_POST['btndefaultbghovertwo'];
                                                                    $data32 = $_POST['btndefaultborderhovertwo'];
                                                                    $data33 = $_POST['btndefaultcolorhovertwo'];
                                                                    $data34 = $_POST['btnprimaryoutlinebgtwo'];
                                                                    $data35 = $_POST['btnprimaryoutlinebordertwo'];
                                                                    $data36 = $_POST['btnprimaryoutlinecolortwo'];
                                                                    $data37 = $_POST['btnprimaryoutlinebghovertwo'];
                                                                    $data38 = $_POST['btnprimaryoutlineborderhovertwo'];
                                                                    $data39 = $_POST['btnprimaryoutlinecolorhovertwo'];
                                                                    $data40 = $_POST['btnprimaryoutlinewhitebgtwo'];
                                                                    $data41 = $_POST['btnprimaryoutlinewhitebordertwo'];
                                                                    $data42 = $_POST['btnprimaryoutlinewhitecolortwo'];
                                                                    $data43 = $_POST['btnprimaryoutlinewhitebghovertwo'];
                                                                    $data44 = $_POST['btnprimaryoutlinewhiteborderhovertwo'];
                                                                    $data45 = $_POST['btnprimaryoutlinewhitecolorhovertwo'];
                                                                    $data46 = $_POST['btnprimaryoutlinelightbgtwo'];
                                                                    $data47 = $_POST['btnprimaryoutlinelightbordertwo'];
                                                                    $data48 = $_POST['btnprimaryoutlinelightcolortwo'];
                                                                    $data49 = $_POST['btnprimaryoutlinelightbghovertwo'];
                                                                    $data50 = $_POST['btnprimaryoutlinelightborderhovertwo'];
                                                                    $data51 = $_POST['btnprimaryoutlinelightcolorhovertwo'];
                                                                    $data52 = $_POST['textstagscolortwoheading'];
                                                                    $data53 = $_POST['textstagscolortwoheadinghover'];
                                                                    $data54 = $_POST['textstagscolortwoheadinggray'];
                                                                    $data55 = $_POST['textstagscolortwosubheading'];
                                                                    $data56 = $_POST['textstagscolortwotextcolor'];
                                                                    $data57 = $_POST['textstagscolortwotextcoloropacity'];
                                                                    $data58 = $_POST['textstagscolortwoborder'];
                                                                    $data59 = $_POST['textstagscolortwoborderlight'];
                                                                    $data60 = $_POST['textstagscolortwolink'];
                                                                    $data61 = $_POST['textstagscolortwolinkhover'];
                                                                    $data62 = $_POST['sidebarcolorsdefaulttwobg'];
                                                                    $data63 = $_POST['sidebarcolorsdefaulttwoextendbtnbg'];
                                                                    $data64 = $_POST['sidebarcolorsdefaulttwoitembg'];
                                                                    $data65 = $_POST['sidebarcolorsdefaulttwoitemhoverbg'];
                                                                    $data66 = $_POST['sidebarcolorsdefaulttwoitemtext'];
                                                                    $data67 = $_POST['sidebarcolorsdefaulttwoitemicon'];
                                                                    $data68 = $_POST['sidebarcolorsdefaulttwoitemtexthover'];
                                                                    $data69 = $_POST['sidebarcolorsdefaulttwoitemiconhover'];
                                                                    $data70 = $_POST['sidebarcolorsdefaulttwodropdownbg'];
                                                                    $data71 = $_POST['sidebarcolorsdefaulttwodropdowntitle'];
                                                                    $data72 = $_POST['sidebarcolorsdarktwodropdownitembg'];
                                                                    $data73 = $_POST['sidebarcolorsdefaulttwodropdownitemtext'];
                                                                    $data74 = $_POST['sidebarcolorsdefaulttwodropdownitemicon'];
                                                                    $data75 = $_POST['sidebarcolorsdefaulttwodropdownitemtexthover'];
                                                                    $data76 = $_POST['sidebarcolorsdefaulttwodropdownitemiconhover'];
                                                                    $data77 = $_POST['sidebarcolorsdarktwobg'];
                                                                    $data78 = $_POST['sidebarcolorsdarktwoextendbtnbg'];
                                                                    $data79 = $_POST['sidebarcolorsdarktwoitembg'];
                                                                    $data80 = $_POST['sidebarcolorsdarktwoitemhoverbg'];
                                                                    $data81 = $_POST['sidebarcolorsdarktwoitemtext'];
                                                                    $data82 = $_POST['sidebarcolorsdarktwoitemicon'];
                                                                    $data83 = $_POST['sidebarcolorsdarktwoitemtexthover'];
                                                                    $data84 = $_POST['sidebarcolorsdarktwoitemiconhover'];
                                                                    $data85 = $_POST['sidebarcolorsdarktwodropdownbg'];
                                                                    $data86 = $_POST['sidebarcolorsdarktwodropdowntitle'];
                                                                    $data87 = $_POST['sidebarcolorsdarktwodropdownitembg'];
                                                                    $data88 = $_POST['sidebarcolorsdarktwodropdownitemtext'];
                                                                    $data89 = $_POST['sidebarcolorsdarktwodropdownitemicon'];
                                                                    $data90 = $_POST['sidebarcolorsdarktwodropdownitemtexthover'];
                                                                    $data91 = $_POST['sidebarcolorsdarktwodropdownitemiconhover'];
                                                                    $data92 = $_POST['alertbgprimarytwo'];
                                                                    $data93 = $_POST['alertcolorprimarytwo'];
                                                                    $data94 = $_POST['alertbgsecondarytwo'];
                                                                    $data95 = $_POST['alertcolorsecondarytwo'];
                                                                    $data96 = $_POST['alertbgsuccesstwo'];
                                                                    $data97 = $_POST['alertcolorsuccesstwo'];
                                                                    $data98 = $_POST['alertbgdangertwo'];
                                                                    $data99 = $_POST['alertcolordangertwo'];
                                                                    $data100 = $_POST['alertbgwarningtwo'];
                                                                    $data101 = $_POST['alertcolorwarningtwo'];
                                                                    $data102 = $_POST['alertbginfotwo'];
                                                                    $data103 = $_POST['alertcolorinfotwo'];
                                                                    $data104 = $_POST['alertbglighttwo'];
                                                                    $data105 = $_POST['alertcolorlightwot'];
                                                                    $data106 = $_POST['alertbgdarktwo'];
                                                                    $data107 = $_POST['alertcolordarktwo'];
                                                                    $data108 = $_POST['btnlightbgtwo'];
                                                                    $data109 = $_POST['btnlightbordertwo'];
                                                                    $data110 = $_POST['btnlightcolortwo'];
                                                                    $data111 = $_POST['btnlightbghovertwo'];
                                                                    $data112 = $_POST['btnlightborderhovertwo'];
                                                                    $data113 = $_POST['btnlightcolorhovertwo'];
                                                                    $data114 = $_POST['btnlighterbgtwo'];
                                                                    $data115 = $_POST['btnlighterbordertwo'];
                                                                    $data116 = $_POST['btnlightercolortwo'];
                                                                    $data117 = $_POST['btnlighterbghovertwo'];
                                                                    $data118 = $_POST['btnlighterborderhovertwo'];
                                                                    $data119 = $_POST['btnlightercolorhovertwo'];
                                                                    $header = 'body.theme-style-two{';
                                                                    $footer = '}';
                                                                    $titles = [
                                                                        '--background',
                                                                        '--background-2',
                                                                        '--background-3',
                                                                        '--background-4',
                                                                        '--background-5',
                                                                        '--background-6',
                                                                        '--background-7',
                                                                        '--background-8',
                                                                        '--background-9',
                                                                        '--background-10',
                                                                        '--background-11',
                                                                        '--background-12',
                                                                        '--background-13',
                                                                        '--background-14',
                                                                        '--background-15',
                                                                        '--btn-primary-bg',
                                                                        '--btn-primary-border',
                                                                        '--btn-primary-color',
                                                                        '--btn-primary-bg-hover',
                                                                        '--btn-primary-border-hover',
                                                                        '--btn-primary-color-hover',
                                                                        '--btn-primary-light-bg',
                                                                        '--btn-primary-light-border',
                                                                        '--btn-primary-light-color',
                                                                        '--btn-primary-light-bg-hover',
                                                                        '--btn-primary-light-border-hover',
                                                                        '--btn-primary-light-color-hover',
                                                                        '--btn-default-bg',
                                                                        '--btn-default-border',
                                                                        '--btn-default-color',
                                                                        '--btn-default-bg-hover',
                                                                        '--btn-default-border-hover',
                                                                        '--btn-default-color-hover',
                                                                        '--btn-primary-outlin-bg',
                                                                        '--btn-primary-outlin-border',
                                                                        '--btn-primary-outlin-color',
                                                                        '--btn-primary-outlin-bg-hover',
                                                                        '--btn-primary-outlin-border-hover',
                                                                        '--btn-primary-outlin-color-hover',
                                                                        '--btn-primary-outlin-white-bg',
                                                                        '--btn-primary-outlin-white-border',
                                                                        '--btn-primary-outlin-white-color',
                                                                        '--btn-primary-outlin-white-bg-hover',
                                                                        '--btn-primary-outlin-white-border-hover',
                                                                        '--btn-primary-outlin-white-color-hover',
                                                                        '--btn-primary-outlin-light-bg',
                                                                        '--btn-primary-outlin-light-border',
                                                                        '--btn-primary-outlin-light-color',
                                                                        '--btn-primary-outlin-light-bg-hover',
                                                                        '--btn-primary-outlin-light-border-hover',
                                                                        '--btn-primary-outlin-light-color-hover',
                                                                        '--color-h',
                                                                        '--color-h-hover',
                                                                        '--color-gray',
                                                                        '--color-h-sub',
                                                                        '--color-texts',
                                                                        '--color-texts-opacity',
                                                                        '--border-color',
                                                                        '--border-color-light',
                                                                        '--a-link-color',
                                                                        '--a-link-color-hover',
                                                                        '--sidebarcolorsdefaultonebg',
                                                                        '--sidebarcolorsdefaultoneextendbtnbg',
                                                                        '--sidebarcolorsdefaultoneitembg',
                                                                        '--sidebarcolorsdefaultoneitemhoverbg',
                                                                        '--sidebarcolorsdefaultoneitemtext',
                                                                        '--sidebarcolorsdefaultoneitemicon',
                                                                        '--sidebarcolorsdefaultoneitemtexthover',
                                                                        '--sidebarcolorsdefaultoneitemiconhover',
                                                                        '--sidebarcolorsdefaultonedropdownbg',
                                                                        '--sidebarcolorsdefaultonedropdowntitle',
                                                                        '--sidebarcolorsdefaultonedropdownitembg',
                                                                        '--sidebarcolorsdefaultonedropdownitemtext',
                                                                        '--sidebarcolorsdefaultonedropdownitemicon',
                                                                        '--sidebarcolorsdefaultonedropdownitemtexthover',
                                                                        '--sidebarcolorsdefaultonedropdownitemiconhover',
                                                                        '--sidebarcolorsdarkonebg',
                                                                        '--sidebarcolorsdarkoneextendbtnbg',
                                                                        '--sidebarcolorsdarkoneitembg',
                                                                        '--sidebarcolorsdarkoneitemhoverbg',
                                                                        '--sidebarcolorsdarkoneitemtext',
                                                                        '--sidebarcolorsdarkoneitemicon',
                                                                        '--sidebarcolorsdarkoneitemtexthover',
                                                                        '--sidebarcolorsdarkoneitemiconhover',
                                                                        '--sidebarcolorsdarkonedropdownbg',
                                                                        '--sidebarcolorsdarkonedropdowntitle',
                                                                        '--sidebarcolorsdarkonedropdownitembg',
                                                                        '--sidebarcolorsdarkonedropdownitemtext',
                                                                        '--sidebarcolorsdarkonedropdownitemicon',
                                                                        '--sidebarcolorsdarkonedropdownitemtexthover',
                                                                        '--sidebarcolorsdarkonedropdownitemiconhover',
                                                                        '--alertbgprimary',
                                                                        '--alertcolorprimary',
                                                                        '--alertbgsecondary',
                                                                        '--alertcolorsecondary',
                                                                        '--alertbgsuccess',
                                                                        '--alertcolorsuccess',
                                                                        '--alertbgdanger',
                                                                        '--alertcolordanger',
                                                                        '--alertbgwarning',
                                                                        '--alertcolorwarning',
                                                                        '--alertbginfo',
                                                                        '--alertcolorinfo',
                                                                        '--alertbglight',
                                                                        '--alertcolorlight',
                                                                        '--alertbgdark',
                                                                        '--alertcolordark',
                                                                        '--btn-light-bg',
                                                                        '--btn-light-border',
                                                                        '--btn-light-color',
                                                                        '--btn-light-bg-hover',
                                                                        '--btn-light-border-hover',
                                                                        '--btn-light-color-hover',
                                                                        '--btn-lighter-bg',
                                                                        '--btn-lighter-border',
                                                                        '--btn-lighter-color',
                                                                        '--btn-lighter-bg-hover',
                                                                        '--btn-lighter-border-hover',
                                                                        '--btn-lighter-color-hover',
                                                                    ];
                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/green-style.css';
                                                                    $file = fopen($filePath, 'w');
                                                                    fwrite($file, $header . PHP_EOL);
                                                                    $i = 2;
                                                                    while ($i < count($titles)) {
                                                                        fwrite($file, $titles[$i] . ': ' . ${'data' . $i + 1} . ';');
                                                                        ++$i;
                                                                    }
                                                                    fwrite($file, $footer . PHP_EOL);
                                                                    fclose($file);
                                                                }
                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                    $data1 = $_POST['backroundonethree'];
                                                                    $data2 = $_POST['backroundtwothree'];
                                                                    $data3 = $_POST['backroundtreethree'];
                                                                    $data4 = $_POST['backroundfourthree'];
                                                                    $data5 = $_POST['backroundfivethree'];
                                                                    $data6 = $_POST['backroundsixthree'];
                                                                    $data7 = $_POST['backroundsaventhree'];
                                                                    $data8 = $_POST['backroundeightthree'];
                                                                    $data9 = $_POST['backroundninethree'];
                                                                    $data10 = $_POST['backroundtenthree'];
                                                                    $data11 = $_POST['backroundeleventhree'];
                                                                    $data12 = $_POST['backroundtwelvethree'];
                                                                    $data13 = $_POST['backroundthirteenthree'];
                                                                    $data14 = $_POST['backroundfourteenthree'];
                                                                    $data15 = $_POST['backroundfifteenthree'];
                                                                    $data16 = $_POST['btnprimarybgthree'];
                                                                    $data17 = $_POST['btnprimaryborderthree'];
                                                                    $data18 = $_POST['btnprimarycolorthree'];
                                                                    $data19 = $_POST['btnprimarybghoverthree'];
                                                                    $data20 = $_POST['btnprimaryborderhoverthree'];
                                                                    $data21 = $_POST['btnprimarycolorhoverthree'];
                                                                    $data22 = $_POST['btnprimarylightbgthree'];
                                                                    $data23 = $_POST['btnprimarylightborderthree'];
                                                                    $data24 = $_POST['btnprimarylightcolorthree'];
                                                                    $data25 = $_POST['btnprimarylightbghoverthree'];
                                                                    $data26 = $_POST['btnprimarylightborderhoverthree'];
                                                                    $data27 = $_POST['btnprimarylightcolorhoverthree'];
                                                                    $data28 = $_POST['btndefaultbgthree'];
                                                                    $data29 = $_POST['btndefaultborderthree'];
                                                                    $data30 = $_POST['btndefaultcolorthree'];
                                                                    $data31 = $_POST['btndefaultbghoverthree'];
                                                                    $data32 = $_POST['btndefaultborderhoverthree'];
                                                                    $data33 = $_POST['btndefaultcolorhoverthree'];
                                                                    $data34 = $_POST['btnprimaryoutlinebgthree'];
                                                                    $data35 = $_POST['btnprimaryoutlineborderthree'];
                                                                    $data36 = $_POST['btnprimaryoutlinecolorthree'];
                                                                    $data37 = $_POST['btnprimaryoutlinebghoverthree'];
                                                                    $data38 = $_POST['btnprimaryoutlineborderhoverthree'];
                                                                    $data39 = $_POST['btnprimaryoutlinecolorhoverthree'];
                                                                    $data40 = $_POST['btnprimaryoutlinewhitebgthree'];
                                                                    $data41 = $_POST['btnprimaryoutlinewhiteborderthree'];
                                                                    $data42 = $_POST['btnprimaryoutlinewhitecolorthree'];
                                                                    $data43 = $_POST['btnprimaryoutlinewhitebghoverthree'];
                                                                    $data44 = $_POST['btnprimaryoutlinewhiteborderhoverthree'];
                                                                    $data45 = $_POST['btnprimaryoutlinewhitecolorhoverthree'];
                                                                    $data46 = $_POST['btnprimaryoutlinelightbgthree'];
                                                                    $data47 = $_POST['btnprimaryoutlinelightborderthree'];
                                                                    $data48 = $_POST['btnprimaryoutlinelightcolorthree'];
                                                                    $data49 = $_POST['btnprimaryoutlinelightbghoverthree'];
                                                                    $data50 = $_POST['btnprimaryoutlinelightborderhoverthree'];
                                                                    $data51 = $_POST['btnprimaryoutlinelightcolorhoverthree'];
                                                                    $data52 = $_POST['textstagscolorthreeheading'];
                                                                    $data53 = $_POST['textstagscolorthreeheadinghover'];
                                                                    $data54 = $_POST['textstagscolorthreeheadinggray'];
                                                                    $data55 = $_POST['textstagscolorthreesubheading'];
                                                                    $data56 = $_POST['textstagscolorthreetextcolor'];
                                                                    $data57 = $_POST['textstagscolorthreetextcoloropacity'];
                                                                    $data58 = $_POST['textstagscolorthreeborder'];
                                                                    $data59 = $_POST['textstagscolorthreeborderlight'];
                                                                    $data60 = $_POST['textstagscolorthreelink'];
                                                                    $data61 = $_POST['textstagscolorthreelinkhover'];
                                                                    $data62 = $_POST['sidebarcolorsdefaultthreebg'];
                                                                    $data63 = $_POST['sidebarcolorsdefaultthreeextendbtnbg'];
                                                                    $data64 = $_POST['sidebarcolorsdefaultthreeitembg'];
                                                                    $data65 = $_POST['sidebarcolorsdefaultthreeitemhoverbg'];
                                                                    $data66 = $_POST['sidebarcolorsdefaultthreeitemtext'];
                                                                    $data67 = $_POST['sidebarcolorsdefaultthreeitemicon'];
                                                                    $data68 = $_POST['sidebarcolorsdefaultthreeitemtexthover'];
                                                                    $data69 = $_POST['sidebarcolorsdefaultthreeitemiconhover'];
                                                                    $data70 = $_POST['sidebarcolorsdefaultthreedropdownbg'];
                                                                    $data71 = $_POST['sidebarcolorsdefaultthreedropdowntitle'];
                                                                    $data72 = $_POST['sidebarcolorsdarkthreedropdownitembg'];
                                                                    $data73 = $_POST['sidebarcolorsdefaultthreedropdownitemtext'];
                                                                    $data74 = $_POST['sidebarcolorsdefaultthreedropdownitemicon'];
                                                                    $data75 = $_POST['sidebarcolorsdefaultthreedropdownitemtexthover'];
                                                                    $data76 = $_POST['sidebarcolorsdefaultthreedropdownitemiconhover'];
                                                                    $data77 = $_POST['sidebarcolorsdarkthreebg'];
                                                                    $data78 = $_POST['sidebarcolorsdarkthreeextendbtnbg'];
                                                                    $data79 = $_POST['sidebarcolorsdarkthreeitembg'];
                                                                    $data80 = $_POST['sidebarcolorsdarkthreeitemhoverbg'];
                                                                    $data81 = $_POST['sidebarcolorsdarkthreeitemtext'];
                                                                    $data82 = $_POST['sidebarcolorsdarkthreeitemicon'];
                                                                    $data83 = $_POST['sidebarcolorsdarkthreeitemtexthover'];
                                                                    $data84 = $_POST['sidebarcolorsdarkthreeitemiconhover'];
                                                                    $data85 = $_POST['sidebarcolorsdarkthreedropdownbg'];
                                                                    $data86 = $_POST['sidebarcolorsdarkthreedropdowntitle'];
                                                                    $data87 = $_POST['sidebarcolorsdarkthreedropdownitembg'];
                                                                    $data88 = $_POST['sidebarcolorsdarkthreedropdownitemtext'];
                                                                    $data89 = $_POST['sidebarcolorsdarkthreedropdownitemicon'];
                                                                    $data90 = $_POST['sidebarcolorsdarkthreedropdownitemtexthover'];
                                                                    $data91 = $_POST['sidebarcolorsdarkthreedropdownitemiconhover'];
                                                                    $data92 = $_POST['alertbgprimarythree'];
                                                                    $data93 = $_POST['alertcolorprimarythree'];
                                                                    $data94 = $_POST['alertbgsecondarythree'];
                                                                    $data95 = $_POST['alertcolorsecondarythree'];
                                                                    $data96 = $_POST['alertbgsuccessthree'];
                                                                    $data97 = $_POST['alertcolorsuccessthree'];
                                                                    $data98 = $_POST['alertbgdangerthree'];
                                                                    $data99 = $_POST['alertcolordangerthree'];
                                                                    $data100 = $_POST['alertbgwarningthree'];
                                                                    $data101 = $_POST['alertcolorwarningthree'];
                                                                    $data102 = $_POST['alertbginfothree'];
                                                                    $data103 = $_POST['alertcolorinfothree'];
                                                                    $data104 = $_POST['alertbglightthree'];
                                                                    $data105 = $_POST['alertcolorlighthreet'];
                                                                    $data106 = $_POST['alertbgdarkthree'];
                                                                    $data107 = $_POST['alertcolordarkthree'];
                                                                    $data108 = $_POST['btnlightbgthree'];
                                                                    $data109 = $_POST['btnlightborderthree'];
                                                                    $data110 = $_POST['btnlightcolorthree'];
                                                                    $data111 = $_POST['btnlightbghoverthree'];
                                                                    $data112 = $_POST['btnlightborderhoverthree'];
                                                                    $data113 = $_POST['btnlightcolorhoverthree'];
                                                                    $data114 = $_POST['btnlighterbgthree'];
                                                                    $data115 = $_POST['btnlighterborderthree'];
                                                                    $data116 = $_POST['btnlightercolorthree'];
                                                                    $data117 = $_POST['btnlighterbghoverthree'];
                                                                    $data118 = $_POST['btnlighterborderhoverthree'];
                                                                    $data119 = $_POST['btnlightercolorhoverthree'];
                                                                    $header = 'body.theme-style-three{';
                                                                    $footer = '}';
                                                                    $titles = [
                                                                        '--background',
                                                                        '--background-2',
                                                                        '--background-3',
                                                                        '--background-4',
                                                                        '--background-5',
                                                                        '--background-6',
                                                                        '--background-7',
                                                                        '--background-8',
                                                                        '--background-9',
                                                                        '--background-10',
                                                                        '--background-11',
                                                                        '--background-12',
                                                                        '--background-13',
                                                                        '--background-14',
                                                                        '--background-15',
                                                                        '--btn-primary-bg',
                                                                        '--btn-primary-border',
                                                                        '--btn-primary-color',
                                                                        '--btn-primary-bg-hover',
                                                                        '--btn-primary-border-hover',
                                                                        '--btn-primary-color-hover',
                                                                        '--btn-primary-light-bg',
                                                                        '--btn-primary-light-border',
                                                                        '--btn-primary-light-color',
                                                                        '--btn-primary-light-bg-hover',
                                                                        '--btn-primary-light-border-hover',
                                                                        '--btn-primary-light-color-hover',
                                                                        '--btn-default-bg',
                                                                        '--btn-default-border',
                                                                        '--btn-default-color',
                                                                        '--btn-default-bg-hover',
                                                                        '--btn-default-border-hover',
                                                                        '--btn-default-color-hover',
                                                                        '--btn-primary-outlin-bg',
                                                                        '--btn-primary-outlin-border',
                                                                        '--btn-primary-outlin-color',
                                                                        '--btn-primary-outlin-bg-hover',
                                                                        '--btn-primary-outlin-border-hover',
                                                                        '--btn-primary-outlin-color-hover',
                                                                        '--btn-primary-outlin-white-bg',
                                                                        '--btn-primary-outlin-white-border',
                                                                        '--btn-primary-outlin-white-color',
                                                                        '--btn-primary-outlin-white-bg-hover',
                                                                        '--btn-primary-outlin-white-border-hover',
                                                                        '--btn-primary-outlin-white-color-hover',
                                                                        '--btn-primary-outlin-light-bg',
                                                                        '--btn-primary-outlin-light-border',
                                                                        '--btn-primary-outlin-light-color',
                                                                        '--btn-primary-outlin-light-bg-hover',
                                                                        '--btn-primary-outlin-light-border-hover',
                                                                        '--btn-primary-outlin-light-color-hover',
                                                                        '--color-h',
                                                                        '--color-h-hover',
                                                                        '--color-gray',
                                                                        '--color-h-sub',
                                                                        '--color-texts',
                                                                        '--color-texts-opacity',
                                                                        '--border-color',
                                                                        '--border-color-light',
                                                                        '--a-link-color',
                                                                        '--a-link-color-hover',
                                                                        '--sidebarcolorsdefaultonebg',
                                                                        '--sidebarcolorsdefaultoneextendbtnbg',
                                                                        '--sidebarcolorsdefaultoneitembg',
                                                                        '--sidebarcolorsdefaultoneitemhoverbg',
                                                                        '--sidebarcolorsdefaultoneitemtext',
                                                                        '--sidebarcolorsdefaultoneitemicon',
                                                                        '--sidebarcolorsdefaultoneitemtexthover',
                                                                        '--sidebarcolorsdefaultoneitemiconhover',
                                                                        '--sidebarcolorsdefaultonedropdownbg',
                                                                        '--sidebarcolorsdefaultonedropdowntitle',
                                                                        '--sidebarcolorsdefaultonedropdownitembg',
                                                                        '--sidebarcolorsdefaultonedropdownitemtext',
                                                                        '--sidebarcolorsdefaultonedropdownitemicon',
                                                                        '--sidebarcolorsdefaultonedropdownitemtexthover',
                                                                        '--sidebarcolorsdefaultonedropdownitemiconhover',
                                                                        '--sidebarcolorsdarkonebg',
                                                                        '--sidebarcolorsdarkoneextendbtnbg',
                                                                        '--sidebarcolorsdarkoneitembg',
                                                                        '--sidebarcolorsdarkoneitemhoverbg',
                                                                        '--sidebarcolorsdarkoneitemtext',
                                                                        '--sidebarcolorsdarkoneitemicon',
                                                                        '--sidebarcolorsdarkoneitemtexthover',
                                                                        '--sidebarcolorsdarkoneitemiconhover',
                                                                        '--sidebarcolorsdarkonedropdownbg',
                                                                        '--sidebarcolorsdarkonedropdowntitle',
                                                                        '--sidebarcolorsdarkonedropdownitembg',
                                                                        '--sidebarcolorsdarkonedropdownitemtext',
                                                                        '--sidebarcolorsdarkonedropdownitemicon',
                                                                        '--sidebarcolorsdarkonedropdownitemtexthover',
                                                                        '--sidebarcolorsdarkonedropdownitemiconhover',
                                                                        '--alertbgprimary',
                                                                        '--alertcolorprimary',
                                                                        '--alertbgsecondary',
                                                                        '--alertcolorsecondary',
                                                                        '--alertbgsuccess',
                                                                        '--alertcolorsuccess',
                                                                        '--alertbgdanger',
                                                                        '--alertcolordanger',
                                                                        '--alertbgwarning',
                                                                        '--alertcolorwarning',
                                                                        '--alertbginfo',
                                                                        '--alertcolorinfo',
                                                                        '--alertbglight',
                                                                        '--alertcolorlight',
                                                                        '--alertbgdark',
                                                                        '--alertcolordark',
                                                                        '--btn-light-bg',
                                                                        '--btn-light-border',
                                                                        '--btn-light-color',
                                                                        '--btn-light-bg-hover',
                                                                        '--btn-light-border-hover',
                                                                        '--btn-light-color-hover',
                                                                        '--btn-lighter-bg',
                                                                        '--btn-lighter-border',
                                                                        '--btn-lighter-color',
                                                                        '--btn-lighter-bg-hover',
                                                                        '--btn-lighter-border-hover',
                                                                        '--btn-lighter-color-hover',
                                                                    ];
                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/purple-style.css';
                                                                    $file = fopen($filePath, 'w');
                                                                    fwrite($file, $header . PHP_EOL);
                                                                    $i = 2;
                                                                    while ($i < count($titles)) {
                                                                        fwrite($file, $titles[$i] . ': ' . ${'data' . $i + 1} . ';');
                                                                        ++$i;
                                                                    }
                                                                    fwrite($file, $footer . PHP_EOL);
                                                                    fclose($file);
                                                                }
                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                    $data1 = $_POST['backroundonefour'];
                                                                    $data2 = $_POST['backroundtwofour'];
                                                                    $data3 = $_POST['backroundtreefour'];
                                                                    $data4 = $_POST['backroundfourfour'];
                                                                    $data5 = $_POST['backroundfivefour'];
                                                                    $data6 = $_POST['backroundsixfour'];
                                                                    $data7 = $_POST['backroundsavenfour'];
                                                                    $data8 = $_POST['backroundeightfour'];
                                                                    $data9 = $_POST['backroundninefour'];
                                                                    $data10 = $_POST['backroundtenfour'];
                                                                    $data11 = $_POST['backroundelevenfour'];
                                                                    $data12 = $_POST['backroundtwelvefour'];
                                                                    $data13 = $_POST['backroundthirteenfour'];
                                                                    $data14 = $_POST['backroundfourteenfour'];
                                                                    $data15 = $_POST['backroundfifteenfour'];
                                                                    $data16 = $_POST['btnprimarybgfour'];
                                                                    $data17 = $_POST['btnprimaryborderfour'];
                                                                    $data18 = $_POST['btnprimarycolorfour'];
                                                                    $data19 = $_POST['btnprimarybghoverfour'];
                                                                    $data20 = $_POST['btnprimaryborderhoverfour'];
                                                                    $data21 = $_POST['btnprimarycolorhoverfour'];
                                                                    $data22 = $_POST['btnprimarylightbgfour'];
                                                                    $data23 = $_POST['btnprimarylightborderfour'];
                                                                    $data24 = $_POST['btnprimarylightcolorfour'];
                                                                    $data25 = $_POST['btnprimarylightbghoverfour'];
                                                                    $data26 = $_POST['btnprimarylightborderhoverfour'];
                                                                    $data27 = $_POST['btnprimarylightcolorhoverfour'];
                                                                    $data28 = $_POST['btndefaultbgfour'];
                                                                    $data29 = $_POST['btndefaultborderfour'];
                                                                    $data30 = $_POST['btndefaultcolorfour'];
                                                                    $data31 = $_POST['btndefaultbghoverfour'];
                                                                    $data32 = $_POST['btndefaultborderhoverfour'];
                                                                    $data33 = $_POST['btndefaultcolorhoverfour'];
                                                                    $data34 = $_POST['btnprimaryoutlinebgfour'];
                                                                    $data35 = $_POST['btnprimaryoutlineborderfour'];
                                                                    $data36 = $_POST['btnprimaryoutlinecolorfour'];
                                                                    $data37 = $_POST['btnprimaryoutlinebghoverfour'];
                                                                    $data38 = $_POST['btnprimaryoutlineborderhoverfour'];
                                                                    $data39 = $_POST['btnprimaryoutlinecolorhoverfour'];
                                                                    $data40 = $_POST['btnprimaryoutlinewhitebgfour'];
                                                                    $data41 = $_POST['btnprimaryoutlinewhiteborderfour'];
                                                                    $data42 = $_POST['btnprimaryoutlinewhitecolorfour'];
                                                                    $data43 = $_POST['btnprimaryoutlinewhitebghoverfour'];
                                                                    $data44 = $_POST['btnprimaryoutlinewhiteborderhoverfour'];
                                                                    $data45 = $_POST['btnprimaryoutlinewhitecolorhoverfour'];
                                                                    $data46 = $_POST['btnprimaryoutlinelightbgfour'];
                                                                    $data47 = $_POST['btnprimaryoutlinelightborderfour'];
                                                                    $data48 = $_POST['btnprimaryoutlinelightcolorfour'];
                                                                    $data49 = $_POST['btnprimaryoutlinelightbghoverfour'];
                                                                    $data50 = $_POST['btnprimaryoutlinelightborderhoverfour'];
                                                                    $data51 = $_POST['btnprimaryoutlinelightcolorhoverfour'];
                                                                    $data52 = $_POST['textstagscolorfourheading'];
                                                                    $data53 = $_POST['textstagscolorfourheadinghover'];
                                                                    $data54 = $_POST['textstagscolorfourheadinggray'];
                                                                    $data55 = $_POST['textstagscolorfoursubheading'];
                                                                    $data56 = $_POST['textstagscolorfourtextcolor'];
                                                                    $data57 = $_POST['textstagscolorfourtextcoloropacity'];
                                                                    $data58 = $_POST['textstagscolorfourborder'];
                                                                    $data59 = $_POST['textstagscolorfourborderlight'];
                                                                    $data60 = $_POST['textstagscolorfourlink'];
                                                                    $data61 = $_POST['textstagscolorfourlinkhover'];
                                                                    $data62 = $_POST['sidebarcolorsdefaultfourbg'];
                                                                    $data63 = $_POST['sidebarcolorsdefaultfourextendbtnbg'];
                                                                    $data64 = $_POST['sidebarcolorsdefaultfouritembg'];
                                                                    $data65 = $_POST['sidebarcolorsdefaultfouritemhoverbg'];
                                                                    $data66 = $_POST['sidebarcolorsdefaultfouritemtext'];
                                                                    $data67 = $_POST['sidebarcolorsdefaultfouritemicon'];
                                                                    $data68 = $_POST['sidebarcolorsdefaultfouritemtexthover'];
                                                                    $data69 = $_POST['sidebarcolorsdefaultfouritemiconhover'];
                                                                    $data70 = $_POST['sidebarcolorsdefaultfourdropdownbg'];
                                                                    $data71 = $_POST['sidebarcolorsdefaultfourdropdowntitle'];
                                                                    $data72 = $_POST['sidebarcolorsdarkfourdropdownitembg'];
                                                                    $data73 = $_POST['sidebarcolorsdefaultfourdropdownitemtext'];
                                                                    $data74 = $_POST['sidebarcolorsdefaultfourdropdownitemicon'];
                                                                    $data75 = $_POST['sidebarcolorsdefaultfourdropdownitemtexthover'];
                                                                    $data76 = $_POST['sidebarcolorsdefaultfourdropdownitemiconhover'];
                                                                    $data77 = $_POST['sidebarcolorsdarkfourbg'];
                                                                    $data78 = $_POST['sidebarcolorsdarkfourextendbtnbg'];
                                                                    $data79 = $_POST['sidebarcolorsdarkfouritembg'];
                                                                    $data80 = $_POST['sidebarcolorsdarkfouritemhoverbg'];
                                                                    $data81 = $_POST['sidebarcolorsdarkfouritemtext'];
                                                                    $data82 = $_POST['sidebarcolorsdarkfouritemicon'];
                                                                    $data83 = $_POST['sidebarcolorsdarkfouritemtexthover'];
                                                                    $data84 = $_POST['sidebarcolorsdarkfouritemiconhover'];
                                                                    $data85 = $_POST['sidebarcolorsdarkfourdropdownbg'];
                                                                    $data86 = $_POST['sidebarcolorsdarkfourdropdowntitle'];
                                                                    $data87 = $_POST['sidebarcolorsdarkfourdropdownitembg'];
                                                                    $data88 = $_POST['sidebarcolorsdarkfourdropdownitemtext'];
                                                                    $data89 = $_POST['sidebarcolorsdarkfourdropdownitemicon'];
                                                                    $data90 = $_POST['sidebarcolorsdarkfourdropdownitemtexthover'];
                                                                    $data91 = $_POST['sidebarcolorsdarkfourdropdownitemiconhover'];
                                                                    $data92 = $_POST['alertbgprimaryfour'];
                                                                    $data93 = $_POST['alertcolorprimaryfour'];
                                                                    $data94 = $_POST['alertbgsecondaryfour'];
                                                                    $data95 = $_POST['alertcolorsecondaryfour'];
                                                                    $data96 = $_POST['alertbgsuccessfour'];
                                                                    $data97 = $_POST['alertcolorsuccessfour'];
                                                                    $data98 = $_POST['alertbgdangerfour'];
                                                                    $data99 = $_POST['alertcolordangerfour'];
                                                                    $data100 = $_POST['alertbgwarningfour'];
                                                                    $data101 = $_POST['alertcolorwarningfour'];
                                                                    $data102 = $_POST['alertbginfofour'];
                                                                    $data103 = $_POST['alertcolorinfofour'];
                                                                    $data104 = $_POST['alertbglightfour'];
                                                                    $data105 = $_POST['alertcolorlighfourt'];
                                                                    $data106 = $_POST['alertbgdarkfour'];
                                                                    $data107 = $_POST['alertcolordarkfour'];
                                                                    $data108 = $_POST['btnlightbgfour'];
                                                                    $data109 = $_POST['btnlightborderfour'];
                                                                    $data110 = $_POST['btnlightcolorfour'];
                                                                    $data111 = $_POST['btnlightbghoverfour'];
                                                                    $data112 = $_POST['btnlightborderhoverfour'];
                                                                    $data113 = $_POST['btnlightcolorhoverfour'];
                                                                    $data114 = $_POST['btnlighterbgfour'];
                                                                    $data115 = $_POST['btnlighterborderfour'];
                                                                    $data116 = $_POST['btnlightercolorfour'];
                                                                    $data117 = $_POST['btnlighterbghoverfour'];
                                                                    $data118 = $_POST['btnlighterborderhoverfour'];
                                                                    $data119 = $_POST['btnlightercolorhoverfour'];
                                                                    $header = 'body.theme-style-four{';
                                                                    $footer = '}';
                                                                    $titles = [
                                                                        '--background',
                                                                        '--background-2',
                                                                        '--background-3',
                                                                        '--background-4',
                                                                        '--background-5',
                                                                        '--background-6',
                                                                        '--background-7',
                                                                        '--background-8',
                                                                        '--background-9',
                                                                        '--background-10',
                                                                        '--background-11',
                                                                        '--background-12',
                                                                        '--background-13',
                                                                        '--background-14',
                                                                        '--background-15',
                                                                        '--btn-primary-bg',
                                                                        '--btn-primary-border',
                                                                        '--btn-primary-color',
                                                                        '--btn-primary-bg-hover',
                                                                        '--btn-primary-border-hover',
                                                                        '--btn-primary-color-hover',
                                                                        '--btn-primary-light-bg',
                                                                        '--btn-primary-light-border',
                                                                        '--btn-primary-light-color',
                                                                        '--btn-primary-light-bg-hover',
                                                                        '--btn-primary-light-border-hover',
                                                                        '--btn-primary-light-color-hover',
                                                                        '--btn-default-bg',
                                                                        '--btn-default-border',
                                                                        '--btn-default-color',
                                                                        '--btn-default-bg-hover',
                                                                        '--btn-default-border-hover',
                                                                        '--btn-default-color-hover',
                                                                        '--btn-primary-outlin-bg',
                                                                        '--btn-primary-outlin-border',
                                                                        '--btn-primary-outlin-color',
                                                                        '--btn-primary-outlin-bg-hover',
                                                                        '--btn-primary-outlin-border-hover',
                                                                        '--btn-primary-outlin-color-hover',
                                                                        '--btn-primary-outlin-white-bg',
                                                                        '--btn-primary-outlin-white-border',
                                                                        '--btn-primary-outlin-white-color',
                                                                        '--btn-primary-outlin-white-bg-hover',
                                                                        '--btn-primary-outlin-white-border-hover',
                                                                        '--btn-primary-outlin-white-color-hover',
                                                                        '--btn-primary-outlin-light-bg',
                                                                        '--btn-primary-outlin-light-border',
                                                                        '--btn-primary-outlin-light-color',
                                                                        '--btn-primary-outlin-light-bg-hover',
                                                                        '--btn-primary-outlin-light-border-hover',
                                                                        '--btn-primary-outlin-light-color-hover',
                                                                        '--color-h',
                                                                        '--color-h-hover',
                                                                        '--color-gray',
                                                                        '--color-h-sub',
                                                                        '--color-texts',
                                                                        '--color-texts-opacity',
                                                                        '--border-color',
                                                                        '--border-color-light',
                                                                        '--a-link-color',
                                                                        '--a-link-color-hover',
                                                                        '--sidebarcolorsdefaultonebg',
                                                                        '--sidebarcolorsdefaultoneextendbtnbg',
                                                                        '--sidebarcolorsdefaultoneitembg',
                                                                        '--sidebarcolorsdefaultoneitemhoverbg',
                                                                        '--sidebarcolorsdefaultoneitemtext',
                                                                        '--sidebarcolorsdefaultoneitemicon',
                                                                        '--sidebarcolorsdefaultoneitemtexthover',
                                                                        '--sidebarcolorsdefaultoneitemiconhover',
                                                                        '--sidebarcolorsdefaultonedropdownbg',
                                                                        '--sidebarcolorsdefaultonedropdowntitle',
                                                                        '--sidebarcolorsdefaultonedropdownitembg',
                                                                        '--sidebarcolorsdefaultonedropdownitemtext',
                                                                        '--sidebarcolorsdefaultonedropdownitemicon',
                                                                        '--sidebarcolorsdefaultonedropdownitemtexthover',
                                                                        '--sidebarcolorsdefaultonedropdownitemiconhover',
                                                                        '--sidebarcolorsdarkonebg',
                                                                        '--sidebarcolorsdarkoneextendbtnbg',
                                                                        '--sidebarcolorsdarkoneitembg',
                                                                        '--sidebarcolorsdarkoneitemhoverbg',
                                                                        '--sidebarcolorsdarkoneitemtext',
                                                                        '--sidebarcolorsdarkoneitemicon',
                                                                        '--sidebarcolorsdarkoneitemtexthover',
                                                                        '--sidebarcolorsdarkoneitemiconhover',
                                                                        '--sidebarcolorsdarkonedropdownbg',
                                                                        '--sidebarcolorsdarkonedropdowntitle',
                                                                        '--sidebarcolorsdarkonedropdownitembg',
                                                                        '--sidebarcolorsdarkonedropdownitemtext',
                                                                        '--sidebarcolorsdarkonedropdownitemicon',
                                                                        '--sidebarcolorsdarkonedropdownitemtexthover',
                                                                        '--sidebarcolorsdarkonedropdownitemiconhover',
                                                                        '--alertbgprimary',
                                                                        '--alertcolorprimary',
                                                                        '--alertbgsecondary',
                                                                        '--alertcolorsecondary',
                                                                        '--alertbgsuccess',
                                                                        '--alertcolorsuccess',
                                                                        '--alertbgdanger',
                                                                        '--alertcolordanger',
                                                                        '--alertbgwarning',
                                                                        '--alertcolorwarning',
                                                                        '--alertbginfo',
                                                                        '--alertcolorinfo',
                                                                        '--alertbglight',
                                                                        '--alertcolorlight',
                                                                        '--alertbgdark',
                                                                        '--alertcolordark',
                                                                        '--btn-light-bg',
                                                                        '--btn-light-border',
                                                                        '--btn-light-color',
                                                                        '--btn-light-bg-hover',
                                                                        '--btn-light-border-hover',
                                                                        '--btn-light-color-hover',
                                                                        '--btn-lighter-bg',
                                                                        '--btn-lighter-border',
                                                                        '--btn-lighter-color',
                                                                        '--btn-lighter-bg-hover',
                                                                        '--btn-lighter-border-hover',
                                                                        '--btn-lighter-color-hover',
                                                                    ];
                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/red-style.css';
                                                                    $file = fopen($filePath, 'w');
                                                                    fwrite($file, $header . PHP_EOL);
                                                                    $i = 2;
                                                                    while ($i < count($titles)) {
                                                                        fwrite($file, $titles[$i] . ': ' . ${'data' . $i + 1} . ';');
                                                                        ++$i;
                                                                    }
                                                                    fwrite($file, $footer . PHP_EOL);
                                                                    fclose($file);
                                                                }
                                                                $currentVersion = Manager::table('coodiv__control__colors__settings')->value('custom_colors_version');
                                                                $currentVersion = $currentVersion ?: '1.0.0';
                                                                $newVersion = shufy_increment_version($currentVersion);
                                                                Manager::statement('TRUNCATE TABLE coodiv__control__colors__settings');
                                                                $groupid = Manager::table('coodiv__control__colors__settings')->insertGetId([
                                                                    'darkmodefault' => (string) $menu->input($_POST['darkmodefault']),
                                                                    'custom_colors_version' => $newVersion,
                                                                    'allowdarkmode' => (string) $menu->input($_POST['allowdarkmode']),
                                                                    'dafaultthemecolor' => (string) $menu->input($_POST['dafaultthemecolor']),
                                                                    'backroundone' => (string) $menu->input($_POST['backroundone']),
                                                                    'backroundtwo' => (string) $menu->input($_POST['backroundtwo']),
                                                                    'backroundtree' => (string) $menu->input($_POST['backroundtree']),
                                                                    'backroundfour' => (string) $menu->input($_POST['backroundfour']),
                                                                    'backroundfive' => (string) $menu->input($_POST['backroundfive']),
                                                                    'backroundsix' => (string) $menu->input($_POST['backroundsix']),
                                                                    'backroundsaven' => (string) $menu->input($_POST['backroundsaven']),
                                                                    'backroundeight' => (string) $menu->input($_POST['backroundeight']),
                                                                    'backroundnine' => (string) $menu->input($_POST['backroundnine']),
                                                                    'backroundten' => (string) $menu->input($_POST['backroundten']),
                                                                    'backroundeleven' => (string) $menu->input($_POST['backroundeleven']),
                                                                    'backroundtwelve' => (string) $menu->input($_POST['backroundtwelve']),
                                                                    'backroundthirteen' => (string) $menu->input($_POST['backroundthirteen']),
                                                                    'backroundfourteen' => (string) $menu->input($_POST['backroundfourteen']),
                                                                    'backroundfifteen' => (string) $menu->input($_POST['backroundfifteen']),
                                                                    'textstagscoloroneheading' => (string) $menu->input($_POST['textstagscoloroneheading']),
                                                                    'textstagscoloroneheadinghover' => (string) $menu->input($_POST['textstagscoloroneheadinghover']),
                                                                    'textstagscoloroneheadinggray' => (string) $menu->input($_POST['textstagscoloroneheadinggray']),
                                                                    'textstagscoloronesubheading' => (string) $menu->input($_POST['textstagscoloronesubheading']),
                                                                    'textstagscoloronetextcolor' => (string) $menu->input($_POST['textstagscoloronetextcolor']),
                                                                    'textstagscoloronetextcoloropacity' => (string) $menu->input($_POST['textstagscoloronetextcoloropacity']),
                                                                    'textstagscoloroneborder' => (string) $menu->input($_POST['textstagscoloroneborder']),
                                                                    'textstagscoloroneborderlight' => (string) $menu->input($_POST['textstagscoloroneborderlight']),
                                                                    'textstagscoloronelink' => (string) $menu->input($_POST['textstagscoloronelink']),
                                                                    'textstagscoloronelinkhover' => (string) $menu->input($_POST['textstagscoloronelinkhover']),
                                                                    'sidebarcolorsdefaultonebg' => (string) $menu->input($_POST['sidebarcolorsdefaultonebg']),
                                                                    'sidebarcolorsdefaultoneextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdefaultoneextendbtnbg']),
                                                                    'sidebarcolorsdefaultoneitembg' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitembg']),
                                                                    'sidebarcolorsdefaultoneitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitemhoverbg']),
                                                                    'sidebarcolorsdefaultoneitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitemtext']),
                                                                    'sidebarcolorsdefaultoneitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitemicon']),
                                                                    'sidebarcolorsdefaultoneitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitemtexthover']),
                                                                    'sidebarcolorsdefaultoneitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultoneitemiconhover']),
                                                                    'sidebarcolorsdefaultonedropdownbg' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownbg']),
                                                                    'sidebarcolorsdefaultonedropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdowntitle']),
                                                                    'sidebarcolorsdefaultonedropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownitembg']),
                                                                    'sidebarcolorsdefaultonedropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownitemtext']),
                                                                    'sidebarcolorsdefaultonedropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownitemicon']),
                                                                    'sidebarcolorsdefaultonedropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownitemtexthover']),
                                                                    'sidebarcolorsdefaultonedropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultonedropdownitemiconhover']),
                                                                    'sidebarcolorsdarkonebg' => (string) $menu->input($_POST['sidebarcolorsdarkonebg']),
                                                                    'sidebarcolorsdarkoneextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdarkoneextendbtnbg']),
                                                                    'sidebarcolorsdarkoneitembg' => (string) $menu->input($_POST['sidebarcolorsdarkoneitembg']),
                                                                    'sidebarcolorsdarkoneitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdarkoneitemhoverbg']),
                                                                    'sidebarcolorsdarkoneitemtext' => (string) $menu->input($_POST['sidebarcolorsdarkoneitemtext']),
                                                                    'sidebarcolorsdarkoneitemicon' => (string) $menu->input($_POST['sidebarcolorsdarkoneitemicon']),
                                                                    'sidebarcolorsdarkoneitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkoneitemtexthover']),
                                                                    'sidebarcolorsdarkoneitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkoneitemiconhover']),
                                                                    'sidebarcolorsdarkonedropdownbg' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownbg']),
                                                                    'sidebarcolorsdarkonedropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdowntitle']),
                                                                    'sidebarcolorsdarkonedropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownitembg']),
                                                                    'sidebarcolorsdarkonedropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownitemtext']),
                                                                    'sidebarcolorsdarkonedropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownitemicon']),
                                                                    'sidebarcolorsdarkonedropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownitemtexthover']),
                                                                    'sidebarcolorsdarkonedropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkonedropdownitemiconhover']),
                                                                    'btnprimarybg' => (string) $menu->input($_POST['btnprimarybg']),
                                                                    'btnprimaryborder' => (string) $menu->input($_POST['btnprimaryborder']),
                                                                    'btnprimarycolor' => (string) $menu->input($_POST['btnprimarycolor']),
                                                                    'btnprimarybghover' => (string) $menu->input($_POST['btnprimarybghover']),
                                                                    'btnprimaryborderhover' => (string) $menu->input($_POST['btnprimaryborderhover']),
                                                                    'btnprimarycolorhover' => (string) $menu->input($_POST['btnprimarycolorhover']),
                                                                    'btnprimarylightbg' => (string) $menu->input($_POST['btnprimarylightbg']),
                                                                    'btnprimarylightborder' => (string) $menu->input($_POST['btnprimarylightborder']),
                                                                    'btnprimarylightcolor' => (string) $menu->input($_POST['btnprimarylightcolor']),
                                                                    'btnprimarylightbghover' => (string) $menu->input($_POST['btnprimarylightbghover']),
                                                                    'btnprimarylightborderhover' => (string) $menu->input($_POST['btnprimarylightborderhover']),
                                                                    'btnprimarylightcolorhover' => (string) $menu->input($_POST['btnprimarylightcolorhover']),
                                                                    'btndefaultbg' => (string) $menu->input($_POST['btndefaultbg']),
                                                                    'btndefaultborder' => (string) $menu->input($_POST['btndefaultborder']),
                                                                    'btndefaultcolor' => (string) $menu->input($_POST['btndefaultcolor']),
                                                                    'btndefaultbghover' => (string) $menu->input($_POST['btndefaultbghover']),
                                                                    'btndefaultborderhover' => (string) $menu->input($_POST['btndefaultborderhover']),
                                                                    'btndefaultcolorhover' => (string) $menu->input($_POST['btndefaultcolorhover']),
                                                                    'btnprimaryoutlinebg' => (string) $menu->input($_POST['btnprimaryoutlinebg']),
                                                                    'btnprimaryoutlineborder' => (string) $menu->input($_POST['btnprimaryoutlineborder']),
                                                                    'btnprimaryoutlinecolor' => (string) $menu->input($_POST['btnprimaryoutlinecolor']),
                                                                    'btnprimaryoutlinebghover' => (string) $menu->input($_POST['btnprimaryoutlinebghover']),
                                                                    'btnprimaryoutlineborderhover' => (string) $menu->input($_POST['btnprimaryoutlineborderhover']),
                                                                    'btnprimaryoutlinecolorhover' => (string) $menu->input($_POST['btnprimaryoutlinecolorhover']),
                                                                    'btnprimaryoutlinewhitebg' => (string) $menu->input($_POST['btnprimaryoutlinewhitebg']),
                                                                    'btnprimaryoutlinewhiteborder' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborder']),
                                                                    'btnprimaryoutlinewhitecolor' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolor']),
                                                                    'btnprimaryoutlinewhitebghover' => (string) $menu->input($_POST['btnprimaryoutlinewhitebghover']),
                                                                    'btnprimaryoutlinewhiteborderhover' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderhover']),
                                                                    'btnprimaryoutlinewhitecolorhover' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorhover']),
                                                                    'btnprimaryoutlinelightbg' => (string) $menu->input($_POST['btnprimaryoutlinelightbg']),
                                                                    'btnprimaryoutlinelightborder' => (string) $menu->input($_POST['btnprimaryoutlinelightborder']),
                                                                    'btnprimaryoutlinelightcolor' => (string) $menu->input($_POST['btnprimaryoutlinelightcolor']),
                                                                    'btnprimaryoutlinelightbghover' => (string) $menu->input($_POST['btnprimaryoutlinelightbghover']),
                                                                    'btnprimaryoutlinelightborderhover' => (string) $menu->input($_POST['btnprimaryoutlinelightborderhover']),
                                                                    'btnprimaryoutlinelightcolorhover' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorhover']),
                                                                    'btnlightbg' => (string) $menu->input($_POST['btnlightbg']),
                                                                    'btnlightborder' => (string) $menu->input($_POST['btnlightborder']),
                                                                    'btnlightcolor' => (string) $menu->input($_POST['btnlightcolor']),
                                                                    'btnlightbghover' => (string) $menu->input($_POST['btnlightbghover']),
                                                                    'btnlightborderhover' => (string) $menu->input($_POST['btnlightborderhover']),
                                                                    'btnlightcolorhover' => (string) $menu->input($_POST['btnlightcolorhover']),
                                                                    'btnlighterbg' => (string) $menu->input($_POST['btnlighterbg']),
                                                                    'btnlighterborder' => (string) $menu->input($_POST['btnlighterborder']),
                                                                    'btnlightercolor' => (string) $menu->input($_POST['btnlightercolor']),
                                                                    'btnlighterbghover' => (string) $menu->input($_POST['btnlighterbghover']),
                                                                    'btnlighterborderhover' => (string) $menu->input($_POST['btnlighterborderhover']),
                                                                    'btnlightercolorhover' => (string) $menu->input($_POST['btnlightercolorhover']),
                                                                    'alertbgprimary' => (string) $menu->input($_POST['alertbgprimary']),
                                                                    'alertcolorprimary' => (string) $menu->input($_POST['alertcolorprimary']),
                                                                    'alertbgsecondary' => (string) $menu->input($_POST['alertbgsecondary']),
                                                                    'alertcolorsecondary' => (string) $menu->input($_POST['alertcolorsecondary']),
                                                                    'alertbgsuccess' => (string) $menu->input($_POST['alertbgsuccess']),
                                                                    'alertcolorsuccess' => (string) $menu->input($_POST['alertcolorsuccess']),
                                                                    'alertbgdanger' => (string) $menu->input($_POST['alertbgdanger']),
                                                                    'alertcolordanger' => (string) $menu->input($_POST['alertcolordanger']),
                                                                    'alertbgwarning' => (string) $menu->input($_POST['alertbgwarning']),
                                                                    'alertcolorwarning' => (string) $menu->input($_POST['alertcolorwarning']),
                                                                    'alertbginfo' => (string) $menu->input($_POST['alertbginfo']),
                                                                    'alertcolorinfo' => (string) $menu->input($_POST['alertcolorinfo']),
                                                                    'alertbglight' => (string) $menu->input($_POST['alertbglight']),
                                                                    'alertcolorlight' => (string) $menu->input($_POST['alertcolorlight']),
                                                                    'alertbgdark' => (string) $menu->input($_POST['alertbgdark']),
                                                                    'alertcolordark' => (string) $menu->input($_POST['alertcolordark']),
                                                                    'backroundonetwo' => (string) $menu->input($_POST['backroundonetwo']),
                                                                    'backroundtwotwo' => (string) $menu->input($_POST['backroundtwotwo']),
                                                                    'backroundtreetwo' => (string) $menu->input($_POST['backroundtreetwo']),
                                                                    'backroundfourtwo' => (string) $menu->input($_POST['backroundfourtwo']),
                                                                    'backroundfivetwo' => (string) $menu->input($_POST['backroundfivetwo']),
                                                                    'backroundsixtwo' => (string) $menu->input($_POST['backroundsixtwo']),
                                                                    'backroundsaventwo' => (string) $menu->input($_POST['backroundsaventwo']),
                                                                    'backroundeighttwo' => (string) $menu->input($_POST['backroundeighttwo']),
                                                                    'backroundninetwo' => (string) $menu->input($_POST['backroundninetwo']),
                                                                    'backroundtentwo' => (string) $menu->input($_POST['backroundtentwo']),
                                                                    'backroundeleventwo' => (string) $menu->input($_POST['backroundeleventwo']),
                                                                    'backroundtwelvetwo' => (string) $menu->input($_POST['backroundtwelvetwo']),
                                                                    'backroundthirteentwo' => (string) $menu->input($_POST['backroundthirteentwo']),
                                                                    'backroundfourteentwo' => (string) $menu->input($_POST['backroundfourteentwo']),
                                                                    'backroundfifteentwo' => (string) $menu->input($_POST['backroundfifteentwo']),
                                                                    'textstagscolortwoheading' => (string) $menu->input($_POST['textstagscolortwoheading']),
                                                                    'textstagscolortwoheadinghover' => (string) $menu->input($_POST['textstagscolortwoheadinghover']),
                                                                    'textstagscolortwoheadinggray' => (string) $menu->input($_POST['textstagscolortwoheadinggray']),
                                                                    'textstagscolortwosubheading' => (string) $menu->input($_POST['textstagscolortwosubheading']),
                                                                    'textstagscolortwotextcolor' => (string) $menu->input($_POST['textstagscolortwotextcolor']),
                                                                    'textstagscolortwotextcoloropacity' => (string) $menu->input($_POST['textstagscolortwotextcoloropacity']),
                                                                    'textstagscolortwoborder' => (string) $menu->input($_POST['textstagscolortwoborder']),
                                                                    'textstagscolortwoborderlight' => (string) $menu->input($_POST['textstagscolortwoborderlight']),
                                                                    'textstagscolortwolink' => (string) $menu->input($_POST['textstagscolortwolink']),
                                                                    'textstagscolortwolinkhover' => (string) $menu->input($_POST['textstagscolortwolinkhover']),
                                                                    'sidebarcolorsdefaulttwobg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwobg']),
                                                                    'sidebarcolorsdefaulttwoextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoextendbtnbg']),
                                                                    'sidebarcolorsdefaulttwoitembg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitembg']),
                                                                    'sidebarcolorsdefaulttwoitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitemhoverbg']),
                                                                    'sidebarcolorsdefaulttwoitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitemtext']),
                                                                    'sidebarcolorsdefaulttwoitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitemicon']),
                                                                    'sidebarcolorsdefaulttwoitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitemtexthover']),
                                                                    'sidebarcolorsdefaulttwoitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaulttwoitemiconhover']),
                                                                    'sidebarcolorsdefaulttwodropdownbg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownbg']),
                                                                    'sidebarcolorsdefaulttwodropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdowntitle']),
                                                                    'sidebarcolorsdefaulttwodropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownitembg']),
                                                                    'sidebarcolorsdefaulttwodropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownitemtext']),
                                                                    'sidebarcolorsdefaulttwodropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownitemicon']),
                                                                    'sidebarcolorsdefaulttwodropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownitemtexthover']),
                                                                    'sidebarcolorsdefaulttwodropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaulttwodropdownitemiconhover']),
                                                                    'sidebarcolorsdarktwobg' => (string) $menu->input($_POST['sidebarcolorsdarktwobg']),
                                                                    'sidebarcolorsdarktwoextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdarktwoextendbtnbg']),
                                                                    'sidebarcolorsdarktwoitembg' => (string) $menu->input($_POST['sidebarcolorsdarktwoitembg']),
                                                                    'sidebarcolorsdarktwoitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdarktwoitemhoverbg']),
                                                                    'sidebarcolorsdarktwoitemtext' => (string) $menu->input($_POST['sidebarcolorsdarktwoitemtext']),
                                                                    'sidebarcolorsdarktwoitemicon' => (string) $menu->input($_POST['sidebarcolorsdarktwoitemicon']),
                                                                    'sidebarcolorsdarktwoitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarktwoitemtexthover']),
                                                                    'sidebarcolorsdarktwoitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarktwoitemiconhover']),
                                                                    'sidebarcolorsdarktwodropdownbg' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownbg']),
                                                                    'sidebarcolorsdarktwodropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownitembg']),
                                                                    'sidebarcolorsdarktwodropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdowntitle']),
                                                                    'sidebarcolorsdarktwodropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownitemtext']),
                                                                    'sidebarcolorsdarktwodropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownitemicon']),
                                                                    'sidebarcolorsdarktwodropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownitemtexthover']),
                                                                    'sidebarcolorsdarktwodropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarktwodropdownitemiconhover']),
                                                                    'btnprimarybgtwo' => (string) $menu->input($_POST['btnprimarybgtwo']),
                                                                    'btnprimarybordertwo' => (string) $menu->input($_POST['btnprimarybordertwo']),
                                                                    'btnprimarycolortwo' => (string) $menu->input($_POST['btnprimarycolortwo']),
                                                                    'btnprimarybghovertwo' => (string) $menu->input($_POST['btnprimarybghovertwo']),
                                                                    'btnprimaryborderhovertwo' => (string) $menu->input($_POST['btnprimaryborderhovertwo']),
                                                                    'btnprimarycolorhovertwo' => (string) $menu->input($_POST['btnprimarycolorhovertwo']),
                                                                    'btnprimarylightbgtwo' => (string) $menu->input($_POST['btnprimarylightbgtwo']),
                                                                    'btnprimarylightbordertwo' => (string) $menu->input($_POST['btnprimarylightbordertwo']),
                                                                    'btnprimarylightcolortwo' => (string) $menu->input($_POST['btnprimarylightcolortwo']),
                                                                    'btnprimarylightbghovertwo' => (string) $menu->input($_POST['btnprimarylightbghovertwo']),
                                                                    'btnprimarylightborderhovertwo' => (string) $menu->input($_POST['btnprimarylightborderhovertwo']),
                                                                    'btnprimarylightcolorhovertwo' => (string) $menu->input($_POST['btnprimarylightcolorhovertwo']),
                                                                    'btndefaultbgtwo' => (string) $menu->input($_POST['btndefaultbgtwo']),
                                                                    'btndefaultbordertwo' => (string) $menu->input($_POST['btndefaultbordertwo']),
                                                                    'btndefaultcolortwo' => (string) $menu->input($_POST['btndefaultcolortwo']),
                                                                    'btndefaultbghovertwo' => (string) $menu->input($_POST['btndefaultbghovertwo']),
                                                                    'btndefaultborderhovertwo' => (string) $menu->input($_POST['btndefaultborderhovertwo']),
                                                                    'btndefaultcolorhovertwo' => (string) $menu->input($_POST['btndefaultcolorhovertwo']),
                                                                    'btnprimaryoutlinebgtwo' => (string) $menu->input($_POST['btnprimaryoutlinebgtwo']),
                                                                    'btnprimaryoutlinebordertwo' => (string) $menu->input($_POST['btnprimaryoutlinebordertwo']),
                                                                    'btnprimaryoutlinecolortwo' => (string) $menu->input($_POST['btnprimaryoutlinecolortwo']),
                                                                    'btnprimaryoutlinebghovertwo' => (string) $menu->input($_POST['btnprimaryoutlinebghovertwo']),
                                                                    'btnprimaryoutlineborderhovertwo' => (string) $menu->input($_POST['btnprimaryoutlineborderhovertwo']),
                                                                    'btnprimaryoutlinecolorhovertwo' => (string) $menu->input($_POST['btnprimaryoutlinecolorhovertwo']),
                                                                    'btnprimaryoutlinewhitebgtwo' => (string) $menu->input($_POST['btnprimaryoutlinewhitebgtwo']),
                                                                    'btnprimaryoutlinewhitebordertwo' => (string) $menu->input($_POST['btnprimaryoutlinewhitebordertwo']),
                                                                    'btnprimaryoutlinewhitecolortwo' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolortwo']),
                                                                    'btnprimaryoutlinewhitebghovertwo' => (string) $menu->input($_POST['btnprimaryoutlinewhitebghovertwo']),
                                                                    'btnprimaryoutlinewhiteborderhovertwo' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderhovertwo']),
                                                                    'btnprimaryoutlinewhitecolorhovertwo' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorhovertwo']),
                                                                    'btnprimaryoutlinelightbgtwo' => (string) $menu->input($_POST['btnprimaryoutlinelightbgtwo']),
                                                                    'btnprimaryoutlinelightbordertwo' => (string) $menu->input($_POST['btnprimaryoutlinelightbordertwo']),
                                                                    'btnprimaryoutlinelightcolortwo' => (string) $menu->input($_POST['btnprimaryoutlinelightcolortwo']),
                                                                    'btnprimaryoutlinelightbghovertwo' => (string) $menu->input($_POST['btnprimaryoutlinelightbghovertwo']),
                                                                    'btnprimaryoutlinelightborderhovertwo' => (string) $menu->input($_POST['btnprimaryoutlinelightborderhovertwo']),
                                                                    'btnprimaryoutlinelightcolorhovertwo' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorhovertwo']),
                                                                    'btnlightbgtwo' => (string) $menu->input($_POST['btnlightbgtwo']),
                                                                    'btnlightbordertwo' => (string) $menu->input($_POST['btnlightbordertwo']),
                                                                    'btnlightcolortwo' => (string) $menu->input($_POST['btnlightcolortwo']),
                                                                    'btnlightbghovertwo' => (string) $menu->input($_POST['btnlightbghovertwo']),
                                                                    'btnlightborderhovertwo' => (string) $menu->input($_POST['btnlightborderhovertwo']),
                                                                    'btnlightcolorhovertwo' => (string) $menu->input($_POST['btnlightcolorhovertwo']),
                                                                    'btnlighterbgtwo' => (string) $menu->input($_POST['btnlighterbgtwo']),
                                                                    'btnlighterbordertwo' => (string) $menu->input($_POST['btnlighterbordertwo']),
                                                                    'btnlightercolortwo' => (string) $menu->input($_POST['btnlightercolortwo']),
                                                                    'btnlighterbghovertwo' => (string) $menu->input($_POST['btnlighterbghovertwo']),
                                                                    'btnlighterborderhovertwo' => (string) $menu->input($_POST['btnlighterborderhovertwo']),
                                                                    'btnlightercolorhovertwo' => (string) $menu->input($_POST['btnlightercolorhovertwo']),
                                                                    'alertbgprimarytwo' => (string) $menu->input($_POST['alertbgprimarytwo']),
                                                                    'alertcolorprimarytwo' => (string) $menu->input($_POST['alertcolorprimarytwo']),
                                                                    'alertbgsecondarytwo' => (string) $menu->input($_POST['alertbgsecondarytwo']),
                                                                    'alertcolorsecondarytwo' => (string) $menu->input($_POST['alertcolorsecondarytwo']),
                                                                    'alertbgsuccesstwo' => (string) $menu->input($_POST['alertbgsuccesstwo']),
                                                                    'alertcolorsuccesstwo' => (string) $menu->input($_POST['alertcolorsuccesstwo']),
                                                                    'alertbgdangertwo' => (string) $menu->input($_POST['alertbgdangertwo']),
                                                                    'alertcolordangertwo' => (string) $menu->input($_POST['alertcolordangertwo']),
                                                                    'alertbgwarningtwo' => (string) $menu->input($_POST['alertbgwarningtwo']),
                                                                    'alertcolorwarningtwo' => (string) $menu->input($_POST['alertcolorwarningtwo']),
                                                                    'alertbginfotwo' => (string) $menu->input($_POST['alertbginfotwo']),
                                                                    'alertcolorinfotwo' => (string) $menu->input($_POST['alertcolorinfotwo']),
                                                                    'alertbglighttwo' => (string) $menu->input($_POST['alertbglighttwo']),
                                                                    'alertcolorlighttwo' => (string) $menu->input($_POST['alertcolorlighttwo']),
                                                                    'alertbgdarktwo' => (string) $menu->input($_POST['alertbgdarktwo']),
                                                                    'alertcolordarktwo' => (string) $menu->input($_POST['alertcolordark']),
                                                                    'backroundonethree' => (string) $menu->input($_POST['backroundonethree']),
                                                                    'backroundtwothree' => (string) $menu->input($_POST['backroundtwothree']),
                                                                    'backroundtreethree' => (string) $menu->input($_POST['backroundtreethree']),
                                                                    'backroundfourthree' => (string) $menu->input($_POST['backroundfourthree']),
                                                                    'backroundfivethree' => (string) $menu->input($_POST['backroundfivethree']),
                                                                    'backroundsixthree' => (string) $menu->input($_POST['backroundsixthree']),
                                                                    'backroundsaventhree' => (string) $menu->input($_POST['backroundsaventhree']),
                                                                    'backroundeightthree' => (string) $menu->input($_POST['backroundeightthree']),
                                                                    'backroundninethree' => (string) $menu->input($_POST['backroundninethree']),
                                                                    'backroundtenthree' => (string) $menu->input($_POST['backroundtenthree']),
                                                                    'backroundeleventhree' => (string) $menu->input($_POST['backroundeleventhree']),
                                                                    'backroundtwelvethree' => (string) $menu->input($_POST['backroundtwelvethree']),
                                                                    'backroundthirteenthree' => (string) $menu->input($_POST['backroundthirteenthree']),
                                                                    'backroundfourteenthree' => (string) $menu->input($_POST['backroundfourteenthree']),
                                                                    'backroundfifteenthree' => (string) $menu->input($_POST['backroundfifteenthree']),
                                                                    'textstagscolorthreeheading' => (string) $menu->input($_POST['textstagscolorthreeheading']),
                                                                    'textstagscolorthreeheadinghover' => (string) $menu->input($_POST['textstagscolorthreeheadinghover']),
                                                                    'textstagscolorthreeheadinggray' => (string) $menu->input($_POST['textstagscolorthreeheadinggray']),
                                                                    'textstagscolorthreesubheading' => (string) $menu->input($_POST['textstagscolorthreesubheading']),
                                                                    'textstagscolorthreetextcolor' => (string) $menu->input($_POST['textstagscolorthreetextcolor']),
                                                                    'textstagscolorthreetextcoloropacity' => (string) $menu->input($_POST['textstagscolorthreetextcoloropacity']),
                                                                    'textstagscolorthreeborder' => (string) $menu->input($_POST['textstagscolorthreeborder']),
                                                                    'textstagscolorthreeborderlight' => (string) $menu->input($_POST['textstagscolorthreeborderlight']),
                                                                    'textstagscolorthreelink' => (string) $menu->input($_POST['textstagscolorthreelink']),
                                                                    'textstagscolorthreelinkhover' => (string) $menu->input($_POST['textstagscolorthreelinkhover']),
                                                                    'sidebarcolorsdefaultthreebg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreebg']),
                                                                    'sidebarcolorsdefaultthreeextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeextendbtnbg']),
                                                                    'sidebarcolorsdefaultthreeitembg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitembg']),
                                                                    'sidebarcolorsdefaultthreeitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitemhoverbg']),
                                                                    'sidebarcolorsdefaultthreeitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitemtext']),
                                                                    'sidebarcolorsdefaultthreeitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitemicon']),
                                                                    'sidebarcolorsdefaultthreeitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitemtexthover']),
                                                                    'sidebarcolorsdefaultthreeitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultthreeitemiconhover']),
                                                                    'sidebarcolorsdefaultthreedropdownbg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownbg']),
                                                                    'sidebarcolorsdefaultthreedropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdowntitle']),
                                                                    'sidebarcolorsdefaultthreedropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownitembg']),
                                                                    'sidebarcolorsdefaultthreedropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownitemtext']),
                                                                    'sidebarcolorsdefaultthreedropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownitemicon']),
                                                                    'sidebarcolorsdefaultthreedropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownitemtexthover']),
                                                                    'sidebarcolorsdefaultthreedropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultthreedropdownitemiconhover']),
                                                                    'sidebarcolorsdarkthreebg' => (string) $menu->input($_POST['sidebarcolorsdarkthreebg']),
                                                                    'sidebarcolorsdarkthreeextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdarkthreeextendbtnbg']),
                                                                    'sidebarcolorsdarkthreeitembg' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitembg']),
                                                                    'sidebarcolorsdarkthreeitemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitemhoverbg']),
                                                                    'sidebarcolorsdarkthreeitemtext' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitemtext']),
                                                                    'sidebarcolorsdarkthreeitemicon' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitemicon']),
                                                                    'sidebarcolorsdarkthreeitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitemtexthover']),
                                                                    'sidebarcolorsdarkthreeitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkthreeitemiconhover']),
                                                                    'sidebarcolorsdarkthreedropdownbg' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownbg']),
                                                                    'sidebarcolorsdarkthreedropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownitembg']),
                                                                    'sidebarcolorsdarkthreedropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdowntitle']),
                                                                    'sidebarcolorsdarkthreedropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownitemtext']),
                                                                    'sidebarcolorsdarkthreedropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownitemicon']),
                                                                    'sidebarcolorsdarkthreedropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownitemtexthover']),
                                                                    'sidebarcolorsdarkthreedropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkthreedropdownitemiconhover']),
                                                                    'btnprimarybgthree' => (string) $menu->input($_POST['btnprimarybgthree']),
                                                                    'btnprimaryborderthree' => (string) $menu->input($_POST['btnprimaryborderthree']),
                                                                    'btnprimarycolorthree' => (string) $menu->input($_POST['btnprimarycolorthree']),
                                                                    'btnprimarybghoverthree' => (string) $menu->input($_POST['btnprimarybghoverthree']),
                                                                    'btnprimaryborderhoverthree' => (string) $menu->input($_POST['btnprimaryborderhoverthree']),
                                                                    'btnprimarycolorhoverthree' => (string) $menu->input($_POST['btnprimarycolorhoverthree']),
                                                                    'btnprimarylightbgthree' => (string) $menu->input($_POST['btnprimarylightbgthree']),
                                                                    'btnprimarylightborderthree' => (string) $menu->input($_POST['btnprimarylightborderthree']),
                                                                    'btnprimarylightcolorthree' => (string) $menu->input($_POST['btnprimarylightcolorthree']),
                                                                    'btnprimarylightbghoverthree' => (string) $menu->input($_POST['btnprimarylightbghoverthree']),
                                                                    'btnprimarylightborderhoverthree' => (string) $menu->input($_POST['btnprimarylightborderhoverthree']),
                                                                    'btnprimarylightcolorhoverthree' => (string) $menu->input($_POST['btnprimarylightcolorhoverthree']),
                                                                    'btndefaultbgthree' => (string) $menu->input($_POST['btndefaultbgthree']),
                                                                    'btndefaultborderthree' => (string) $menu->input($_POST['btndefaultborderthree']),
                                                                    'btndefaultcolorthree' => (string) $menu->input($_POST['btndefaultcolorthree']),
                                                                    'btndefaultbghoverthree' => (string) $menu->input($_POST['btndefaultbghoverthree']),
                                                                    'btndefaultborderhoverthree' => (string) $menu->input($_POST['btndefaultborderhoverthree']),
                                                                    'btndefaultcolorhoverthree' => (string) $menu->input($_POST['btndefaultcolorhoverthree']),
                                                                    'btnprimaryoutlinebgthree' => (string) $menu->input($_POST['btnprimaryoutlinebgthree']),
                                                                    'btnprimaryoutlineborderthree' => (string) $menu->input($_POST['btnprimaryoutlineborderthree']),
                                                                    'btnprimaryoutlinecolorthree' => (string) $menu->input($_POST['btnprimaryoutlinecolorthree']),
                                                                    'btnprimaryoutlinebghoverthree' => (string) $menu->input($_POST['btnprimaryoutlinebghoverthree']),
                                                                    'btnprimaryoutlineborderhoverthree' => (string) $menu->input($_POST['btnprimaryoutlineborderhoverthree']),
                                                                    'btnprimaryoutlinecolorhoverthree' => (string) $menu->input($_POST['btnprimaryoutlinecolorhoverthree']),
                                                                    'btnprimaryoutlinewhitebgthree' => (string) $menu->input($_POST['btnprimaryoutlinewhitebgthree']),
                                                                    'btnprimaryoutlinewhiteborderthree' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderthree']),
                                                                    'btnprimaryoutlinewhitecolorthree' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorthree']),
                                                                    'btnprimaryoutlinewhitebghoverthree' => (string) $menu->input($_POST['btnprimaryoutlinewhitebghoverthree']),
                                                                    'btnprimaryoutlinewhiteborderhoverthree' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderhoverthree']),
                                                                    'btnprimaryoutlinewhitecolorhoverthree' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorhoverthree']),
                                                                    'btnprimaryoutlinelightbgthree' => (string) $menu->input($_POST['btnprimaryoutlinelightbgthree']),
                                                                    'btnprimaryoutlinelightborderthree' => (string) $menu->input($_POST['btnprimaryoutlinelightborderthree']),
                                                                    'btnprimaryoutlinelightcolorthree' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorthree']),
                                                                    'btnprimaryoutlinelightbghoverthree' => (string) $menu->input($_POST['btnprimaryoutlinelightbghoverthree']),
                                                                    'btnprimaryoutlinelightborderhoverthree' => (string) $menu->input($_POST['btnprimaryoutlinelightborderhoverthree']),
                                                                    'btnprimaryoutlinelightcolorhoverthree' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorhoverthree']),
                                                                    'btnlightbgthree' => (string) $menu->input($_POST['btnlightbgthree']),
                                                                    'btnlightborderthree' => (string) $menu->input($_POST['btnlightborderthree']),
                                                                    'btnlightcolorthree' => (string) $menu->input($_POST['btnlightcolorthree']),
                                                                    'btnlightbghoverthree' => (string) $menu->input($_POST['btnlightbghoverthree']),
                                                                    'btnlightborderhoverthree' => (string) $menu->input($_POST['btnlightborderhoverthree']),
                                                                    'btnlightcolorhoverthree' => (string) $menu->input($_POST['btnlightcolorhoverthree']),
                                                                    'btnlighterbgthree' => (string) $menu->input($_POST['btnlighterbgthree']),
                                                                    'btnlighterborderthree' => (string) $menu->input($_POST['btnlighterborderthree']),
                                                                    'btnlightercolorthree' => (string) $menu->input($_POST['btnlightercolorthree']),
                                                                    'btnlighterbghoverthree' => (string) $menu->input($_POST['btnlighterbghoverthree']),
                                                                    'btnlighterborderhoverthree' => (string) $menu->input($_POST['btnlighterborderhoverthree']),
                                                                    'btnlightercolorhoverthree' => (string) $menu->input($_POST['btnlightercolorhoverthree']),
                                                                    'alertbgprimarythree' => (string) $menu->input($_POST['alertbgprimarythree']),
                                                                    'alertcolorprimarythree' => (string) $menu->input($_POST['alertcolorprimarythree']),
                                                                    'alertbgsecondarythree' => (string) $menu->input($_POST['alertbgsecondarythree']),
                                                                    'alertcolorsecondarythree' => (string) $menu->input($_POST['alertcolorsecondarythree']),
                                                                    'alertbgsuccessthree' => (string) $menu->input($_POST['alertbgsuccessthree']),
                                                                    'alertcolorsuccessthree' => (string) $menu->input($_POST['alertcolorsuccessthree']),
                                                                    'alertbgdangerthree' => (string) $menu->input($_POST['alertbgdangerthree']),
                                                                    'alertcolordangerthree' => (string) $menu->input($_POST['alertcolordangerthree']),
                                                                    'alertbgwarningthree' => (string) $menu->input($_POST['alertbgwarningthree']),
                                                                    'alertcolorwarningthree' => (string) $menu->input($_POST['alertcolorwarningthree']),
                                                                    'alertbginfothree' => (string) $menu->input($_POST['alertbginfothree']),
                                                                    'alertcolorinfothree' => (string) $menu->input($_POST['alertcolorinfothree']),
                                                                    'alertbglightthree' => (string) $menu->input($_POST['alertbglightthree']),
                                                                    'alertcolorlightthree' => (string) $menu->input($_POST['alertcolorlightthree']),
                                                                    'alertbgdarkthree' => (string) $menu->input($_POST['alertbgdarkthree']),
                                                                    'alertcolordarkthree' => (string) $menu->input($_POST['alertcolordarkthree']),
                                                                    'backroundonefour' => (string) $menu->input($_POST['backroundonefour']),
                                                                    'backroundtwofour' => (string) $menu->input($_POST['backroundtwofour']),
                                                                    'backroundtreefour' => (string) $menu->input($_POST['backroundtreefour']),
                                                                    'backroundfourfour' => (string) $menu->input($_POST['backroundfourfour']),
                                                                    'backroundfivefour' => (string) $menu->input($_POST['backroundfivefour']),
                                                                    'backroundsixfour' => (string) $menu->input($_POST['backroundsixfour']),
                                                                    'backroundsavenfour' => (string) $menu->input($_POST['backroundsavenfour']),
                                                                    'backroundeightfour' => (string) $menu->input($_POST['backroundeightfour']),
                                                                    'backroundninefour' => (string) $menu->input($_POST['backroundninefour']),
                                                                    'backroundtenfour' => (string) $menu->input($_POST['backroundtenfour']),
                                                                    'backroundelevenfour' => (string) $menu->input($_POST['backroundelevenfour']),
                                                                    'backroundtwelvefour' => (string) $menu->input($_POST['backroundtwelvefour']),
                                                                    'backroundthirteenfour' => (string) $menu->input($_POST['backroundthirteenfour']),
                                                                    'backroundfourteenfour' => (string) $menu->input($_POST['backroundfourteenfour']),
                                                                    'backroundfifteenfour' => (string) $menu->input($_POST['backroundfifteenfour']),
                                                                    'textstagscolorfourheading' => (string) $menu->input($_POST['textstagscolorfourheading']),
                                                                    'textstagscolorfourheadinghover' => (string) $menu->input($_POST['textstagscolorfourheadinghover']),
                                                                    'textstagscolorfourheadinggray' => (string) $menu->input($_POST['textstagscolorfourheadinggray']),
                                                                    'textstagscolorfoursubheading' => (string) $menu->input($_POST['textstagscolorfoursubheading']),
                                                                    'textstagscolorfourtextcolor' => (string) $menu->input($_POST['textstagscolorfourtextcolor']),
                                                                    'textstagscolorfourtextcoloropacity' => (string) $menu->input($_POST['textstagscolorfourtextcoloropacity']),
                                                                    'textstagscolorfourborder' => (string) $menu->input($_POST['textstagscolorfourborder']),
                                                                    'textstagscolorfourborderlight' => (string) $menu->input($_POST['textstagscolorfourborderlight']),
                                                                    'textstagscolorfourlink' => (string) $menu->input($_POST['textstagscolorfourlink']),
                                                                    'textstagscolorfourlinkhover' => (string) $menu->input($_POST['textstagscolorfourlinkhover']),
                                                                    'sidebarcolorsdefaultfourbg' => (string) $menu->input($_POST['sidebarcolorsdefaultfourbg']),
                                                                    'sidebarcolorsdefaultfourextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdefaultfourextendbtnbg']),
                                                                    'sidebarcolorsdefaultfouritembg' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritembg']),
                                                                    'sidebarcolorsdefaultfouritemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritemhoverbg']),
                                                                    'sidebarcolorsdefaultfouritemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritemtext']),
                                                                    'sidebarcolorsdefaultfouritemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritemicon']),
                                                                    'sidebarcolorsdefaultfouritemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritemtexthover']),
                                                                    'sidebarcolorsdefaultfouritemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultfouritemiconhover']),
                                                                    'sidebarcolorsdefaultfourdropdownbg' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownbg']),
                                                                    'sidebarcolorsdefaultfourdropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdowntitle']),
                                                                    'sidebarcolorsdefaultfourdropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownitembg']),
                                                                    'sidebarcolorsdefaultfourdropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownitemtext']),
                                                                    'sidebarcolorsdefaultfourdropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownitemicon']),
                                                                    'sidebarcolorsdefaultfourdropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownitemtexthover']),
                                                                    'sidebarcolorsdefaultfourdropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdefaultfourdropdownitemiconhover']),
                                                                    'sidebarcolorsdarkfourbg' => (string) $menu->input($_POST['sidebarcolorsdarkfourbg']),
                                                                    'sidebarcolorsdarkfourextendbtnbg' => (string) $menu->input($_POST['sidebarcolorsdarkfourextendbtnbg']),
                                                                    'sidebarcolorsdarkfouritembg' => (string) $menu->input($_POST['sidebarcolorsdarkfouritembg']),
                                                                    'sidebarcolorsdarkfouritemhoverbg' => (string) $menu->input($_POST['sidebarcolorsdarkfouritemhoverbg']),
                                                                    'sidebarcolorsdarkfouritemtext' => (string) $menu->input($_POST['sidebarcolorsdarkfouritemtext']),
                                                                    'sidebarcolorsdarkfouritemicon' => (string) $menu->input($_POST['sidebarcolorsdarkfouritemicon']),
                                                                    'sidebarcolorsdarkfouritemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkfouritemtexthover']),
                                                                    'sidebarcolorsdarkfouritemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkfouritemiconhover']),
                                                                    'sidebarcolorsdarkfourdropdownbg' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownbg']),
                                                                    'sidebarcolorsdarkfourdropdowntitle' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdowntitle']),
                                                                    'sidebarcolorsdarkfourdropdownitembg' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownitembg']),
                                                                    'sidebarcolorsdarkfourdropdownitemtext' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownitemtext']),
                                                                    'sidebarcolorsdarkfourdropdownitemicon' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownitemicon']),
                                                                    'sidebarcolorsdarkfourdropdownitemtexthover' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownitemtexthover']),
                                                                    'sidebarcolorsdarkfourdropdownitemiconhover' => (string) $menu->input($_POST['sidebarcolorsdarkfourdropdownitemiconhover']),
                                                                    'btnprimarybgfour' => (string) $menu->input($_POST['btnprimarybgfour']),
                                                                    'btnprimaryborderfour' => (string) $menu->input($_POST['btnprimaryborderfour']),
                                                                    'btnprimarycolorfour' => (string) $menu->input($_POST['btnprimarycolorfour']),
                                                                    'btnprimarybghoverfour' => (string) $menu->input($_POST['btnprimarybghoverfour']),
                                                                    'btnprimaryborderhoverfour' => (string) $menu->input($_POST['btnprimaryborderhoverfour']),
                                                                    'btnprimarycolorhoverfour' => (string) $menu->input($_POST['btnprimarycolorhoverfour']),
                                                                    'btnprimarylightbgfour' => (string) $menu->input($_POST['btnprimarylightbgfour']),
                                                                    'btnprimarylightborderfour' => (string) $menu->input($_POST['btnprimarylightborderfour']),
                                                                    'btnprimarylightcolorfour' => (string) $menu->input($_POST['btnprimarylightcolorfour']),
                                                                    'btnprimarylightbghoverfour' => (string) $menu->input($_POST['btnprimarylightbghoverfour']),
                                                                    'btnprimarylightborderhoverfour' => (string) $menu->input($_POST['btnprimarylightborderhoverfour']),
                                                                    'btnprimarylightcolorhoverfour' => (string) $menu->input($_POST['btnprimarylightcolorhoverfour']),
                                                                    'btndefaultbgfour' => (string) $menu->input($_POST['btndefaultbgfour']),
                                                                    'btndefaultborderfour' => (string) $menu->input($_POST['btndefaultborderfour']),
                                                                    'btndefaultcolorfour' => (string) $menu->input($_POST['btndefaultcolorfour']),
                                                                    'btndefaultbghoverfour' => (string) $menu->input($_POST['btndefaultbghoverfour']),
                                                                    'btndefaultborderhoverfour' => (string) $menu->input($_POST['btndefaultborderhoverfour']),
                                                                    'btndefaultcolorhoverfour' => (string) $menu->input($_POST['btndefaultcolorhoverfour']),
                                                                    'btnprimaryoutlinebgfour' => (string) $menu->input($_POST['btnprimaryoutlinebgfour']),
                                                                    'btnprimaryoutlineborderfour' => (string) $menu->input($_POST['btnprimaryoutlineborderfour']),
                                                                    'btnprimaryoutlinecolorfour' => (string) $menu->input($_POST['btnprimaryoutlinecolorfour']),
                                                                    'btnprimaryoutlinebghoverfour' => (string) $menu->input($_POST['btnprimaryoutlinebghoverfour']),
                                                                    'btnprimaryoutlineborderhoverfour' => (string) $menu->input($_POST['btnprimaryoutlineborderhoverfour']),
                                                                    'btnprimaryoutlinecolorhoverfour' => (string) $menu->input($_POST['btnprimaryoutlinecolorhoverfour']),
                                                                    'btnprimaryoutlinewhitebgfour' => (string) $menu->input($_POST['btnprimaryoutlinewhitebgfour']),
                                                                    'btnprimaryoutlinewhiteborderfour' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderfour']),
                                                                    'btnprimaryoutlinewhitecolorfour' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorfour']),
                                                                    'btnprimaryoutlinewhitebghoverfour' => (string) $menu->input($_POST['btnprimaryoutlinewhitebghoverfour']),
                                                                    'btnprimaryoutlinewhiteborderhoverfour' => (string) $menu->input($_POST['btnprimaryoutlinewhiteborderhoverfour']),
                                                                    'btnprimaryoutlinewhitecolorhoverfour' => (string) $menu->input($_POST['btnprimaryoutlinewhitecolorhoverfour']),
                                                                    'btnprimaryoutlinelightbgfour' => (string) $menu->input($_POST['btnprimaryoutlinelightbgfour']),
                                                                    'btnprimaryoutlinelightborderfour' => (string) $menu->input($_POST['btnprimaryoutlinelightborderfour']),
                                                                    'btnprimaryoutlinelightcolorfour' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorfour']),
                                                                    'btnprimaryoutlinelightbghoverfour' => (string) $menu->input($_POST['btnprimaryoutlinelightbghoverfour']),
                                                                    'btnprimaryoutlinelightborderhoverfour' => (string) $menu->input($_POST['btnprimaryoutlinelightborderhoverfour']),
                                                                    'btnprimaryoutlinelightcolorhoverfour' => (string) $menu->input($_POST['btnprimaryoutlinelightcolorhoverfour']),
                                                                    'btnlightbgfour' => (string) $menu->input($_POST['btnlightbgfour']),
                                                                    'btnlightborderfour' => (string) $menu->input($_POST['btnlightborderfour']),
                                                                    'btnlightcolorfour' => (string) $menu->input($_POST['btnlightcolorfour']),
                                                                    'btnlightbghoverfour' => (string) $menu->input($_POST['btnlightbghoverfour']),
                                                                    'btnlightborderhoverfour' => (string) $menu->input($_POST['btnlightborderhoverfour']),
                                                                    'btnlightcolorhoverfour' => (string) $menu->input($_POST['btnlightcolorhoverfour']),
                                                                    'btnlighterbgfour' => (string) $menu->input($_POST['btnlighterbgfour']),
                                                                    'btnlighterborderfour' => (string) $menu->input($_POST['btnlighterborderfour']),
                                                                    'btnlightercolorfour' => (string) $menu->input($_POST['btnlightercolorfour']),
                                                                    'btnlighterbghoverfour' => (string) $menu->input($_POST['btnlighterbghoverfour']),
                                                                    'btnlighterborderhoverfour' => (string) $menu->input($_POST['btnlighterborderhoverfour']),
                                                                    'btnlightercolorhoverfour' => (string) $menu->input($_POST['btnlightercolorhoverfour']),
                                                                    'alertbgprimaryfour' => (string) $menu->input($_POST['alertbgprimaryfour']),
                                                                    'alertcolorprimaryfour' => (string) $menu->input($_POST['alertcolorprimaryfour']),
                                                                    'alertbgsecondaryfour' => (string) $menu->input($_POST['alertbgsecondaryfour']),
                                                                    'alertcolorsecondaryfour' => (string) $menu->input($_POST['alertcolorsecondaryfour']),
                                                                    'alertbgsuccessfour' => (string) $menu->input($_POST['alertbgsuccessfour']),
                                                                    'alertcolorsuccessfour' => (string) $menu->input($_POST['alertcolorsuccessfour']),
                                                                    'alertbgdangerfour' => (string) $menu->input($_POST['alertbgdangerfour']),
                                                                    'alertcolordangerfour' => (string) $menu->input($_POST['alertcolordangerfour']),
                                                                    'alertbgwarningfour' => (string) $menu->input($_POST['alertbgwarningfour']),
                                                                    'alertcolorwarningfour' => (string) $menu->input($_POST['alertcolorwarningfour']),
                                                                    'alertbginfofour' => (string) $menu->input($_POST['alertbginfofour']),
                                                                    'alertcolorinfofour' => (string) $menu->input($_POST['alertcolorinfofour']),
                                                                    'alertbglightfour' => (string) $menu->input($_POST['alertbglightfour']),
                                                                    'alertcolorlightfour' => (string) $menu->input($_POST['alertcolorlightfour']),
                                                                    'alertbgdarkfour' => (string) $menu->input($_POST['alertbgdarkfour']),
                                                                    'alertcolordarkfour' => (string) $menu->input($_POST['alertcolordarkfour']),
                                                                ]);
                                                                try {
                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=styleoptions&success=1', [
                                                                        'message' => 'Shufytheme style options have been saved successfully.',
                                                                        'custom_colors_version' => $newVersion,
                                                                    ]);
                                                                } catch (\Exception $e) {
                                                                    exit('Error: ' . $e->getMessage());
                                                                }
                                                            } else {
                                                                if ($action == 'resetstyleoptions') {
                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                    $filePath1 = ROOTDIR . '/modules/addons/shufyTheme/css-values/default-style.css';
                                                                    $filePath2 = ROOTDIR . '/modules/addons/shufyTheme/css-values/green-style.css';
                                                                    $filePath3 = ROOTDIR . '/modules/addons/shufyTheme/css-values/purple-style.css';
                                                                    $filePath4 = ROOTDIR . '/modules/addons/shufyTheme/css-values/red-style.css';
                                                                    file_put_contents($filePath1, '');
                                                                    file_put_contents($filePath2, '');
                                                                    file_put_contents($filePath3, '');
                                                                    file_put_contents($filePath4, '');
                                                                    $tableName = 'coodiv__control__colors__settings';
                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                    $updateData = array_fill_keys($columns, '');
                                                                    Manager::table($tableName)->update($updateData);
                                                                    $menu->redirect(MODURL . '&action=styleoptions&success=1');
                                                                    try {
                                                                        exit;
                                                                    } catch (\Exception $e) {
                                                                        exit('Error: ' . $e->getMessage());
                                                                    }
                                                                } else {
                                                                    if ($action == 'exportstyleoptions') {
                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                        $themeOptionData = Manager::table('coodiv__control__colors__settings')->get();
                                                                        $csvData = [];
                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                        foreach ($themeOptionData as $row) {
                                                                            $csvData[] = (array) $row;
                                                                        }
                                                                        $csvContent = implode("\n", array_map(function ($row) {
                                                                            return implode(',', $row);
                                                                        }, $csvData));
                                                                        header('Content-Type: text/csv');
                                                                        header('Content-Disposition: attachment; filename="shufytheme_styleoptions_exported_data.csv"');
                                                                        echo $csvContent;
                                                                        try {
                                                                            exit;
                                                                        } catch (\Exception $e) {
                                                                            exit('Error: ' . $e->getMessage());
                                                                        }
                                                                    } else {
                                                                        if ($action == 'importstyleoptions') {
                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                $columns = array_shift($csvData);
                                                                                $validData = true;
                                                                                $invalidRow = null;
                                                                                foreach ($csvData as $index => $row) {
                                                                                    if (count($row) !== count($columns)) {
                                                                                        $validData = false;
                                                                                        $invalidRow = $index + 1;
                                                                                        break;
                                                                                    }
                                                                                }
                                                                                if ($validData) {
                                                                                    Manager::table('coodiv__control__colors__settings')->truncate();
                                                                                    foreach ($csvData as $row) {
                                                                                        $data = array_combine($columns, $row);
                                                                                        Manager::table('coodiv__control__colors__settings')->insert($data);
                                                                                    }
                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                    $menu->redirect(MODURL . '&action=styleoptions&success=1');
                                                                                    exit;
                                                                                } else {
                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                }
                                                                            } else {
                                                                                echo 'Error uploading file.';
                                                                            }
                                                                            try {
                                                                                exit;
                                                                            } catch (\Exception $e) {
                                                                                exit('Error: ' . $e->getMessage());
                                                                            }
                                                                        } else {
                                                                            if ($action == 'typpoptions') {
                                                                                $themesettingid = '1';
                                                                                $smarty->assign('themesettingid', $themesettingid);
                                                                                $getItemInfo = Manager::table('coodiv__control__typography__settings')->where('id', $themesettingid)->get();
                                                                                $themesetting = $menu->fromMYSQL($getItemInfo);
                                                                                $smarty->assign('themetyposetting', $themesetting[0] ?? []);
                                                                                $templateFile = 'typpoptions.tpl';
                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme Typography settings');
                                                                            } elseif ($action == 'applytyppoptions') {
                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                                    $data1 = $_POST['themesettingtyposhufysizeone'];
                                                                                    $data2 = $_POST['themesettingtyposhufysizetwo'];
                                                                                    $data3 = $_POST['themesettingtyposhufysizethree'];
                                                                                    $data4 = $_POST['themesettingtyposhufysizefour'];
                                                                                    $data5 = $_POST['themesettingtyposhufysizefive'];
                                                                                    $data6 = $_POST['themesettingtyposhufysizesix'];
                                                                                    $data7 = $_POST['themesettingtyposhufysizesaven'];
                                                                                    $data8 = $_POST['themesettingtyposhufysizeeight'];
                                                                                    $data9 = $_POST['themesettingtyposhufysizenigne'];
                                                                                    $data10 = $_POST['themesettingtyposhufysizeteen'];
                                                                                    $data11 = $_POST['themesettingtyposhufysizeeleven'];
                                                                                    $data12 = $_POST['themesettingtyposhufysizetwelve'];
                                                                                    $data13 = $_POST['themesettingtyposhufysizetherteen'];
                                                                                    $data14 = $_POST['themesettingtypohone'];
                                                                                    $data15 = $_POST['themesettingtypohtwo'];
                                                                                    $data16 = $_POST['themesettingtypohthree'];
                                                                                    $data17 = $_POST['themesettingtypohfour'];
                                                                                    $data18 = $_POST['themesettingtypohfive'];
                                                                                    $data19 = $_POST['themesettingtypohsix'];
                                                                                    $data20 = $_POST['themesettingtypop'];
                                                                                    $data21 = $_POST['themesettingtypobutton'];
                                                                                    $data22 = $_POST['themesettingtyposbutton'];
                                                                                    $header = ':root{';
                                                                                    $footer = '}';
                                                                                    $titles = [
                                                                                        '--coodiv-text-1',
                                                                                        '--coodiv-text-2',
                                                                                        '--coodiv-text-3',
                                                                                        '--coodiv-text-4',
                                                                                        '--coodiv-text-5',
                                                                                        '--coodiv-text-6',
                                                                                        '--coodiv-text-7',
                                                                                        '--coodiv-text-8',
                                                                                        '--coodiv-text-9',
                                                                                        '--coodiv-text-10',
                                                                                        '--coodiv-text-11',
                                                                                        '--coodiv-text-12',
                                                                                        '--coodiv-text-13',
                                                                                        '--h1-font-size',
                                                                                        '--h2-font-size',
                                                                                        '--h3-font-size',
                                                                                        '--h4-font-size',
                                                                                        '--h5-font-size',
                                                                                        '--h6-font-size',
                                                                                        '--p-font-size',
                                                                                        '--button-font-size',
                                                                                        '--small-button-font-size',
                                                                                    ];
                                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/typographie.css';
                                                                                    $file = fopen($filePath, 'w');
                                                                                    fwrite($file, $header . PHP_EOL);
                                                                                    $i = 2;
                                                                                    while ($i < count($titles)) {
                                                                                        $value = ${'data' . $i + 1};
                                                                                        if (!empty($value)) {
                                                                                            fwrite($file, $titles[$i] . ': ' . $value . 'px;');
                                                                                        }
                                                                                        ++$i;
                                                                                    }
                                                                                    fwrite($file, $footer . PHP_EOL);
                                                                                    fclose($file);
                                                                                }
                                                                                Manager::statement('TRUNCATE TABLE coodiv__control__typography__settings');
                                                                                $groupid = Manager::table('coodiv__control__typography__settings')->insertGetId([
                                                                                    'themesettingtyponame' => (string) $menu->input($_POST['themesettingtyponame']),
                                                                                    'themesettingtyponamertl' => (string) $menu->input($_POST['themesettingtyponamertl']),
                                                                                    'themesettingtyposhufysizeone' => (string) $menu->input($_POST['themesettingtyposhufysizeone']),
                                                                                    'themesettingtyposhufysizetwo' => (string) $menu->input($_POST['themesettingtyposhufysizetwo']),
                                                                                    'themesettingtyposhufysizethree' => (string) $menu->input($_POST['themesettingtyposhufysizethree']),
                                                                                    'themesettingtyposhufysizefour' => (string) $menu->input($_POST['themesettingtyposhufysizefour']),
                                                                                    'themesettingtyposhufysizefive' => (string) $menu->input($_POST['themesettingtyposhufysizefive']),
                                                                                    'themesettingtyposhufysizesix' => (string) $menu->input($_POST['themesettingtyposhufysizesix']),
                                                                                    'themesettingtyposhufysizesaven' => (string) $menu->input($_POST['themesettingtyposhufysizesaven']),
                                                                                    'themesettingtyposhufysizeeight' => (string) $menu->input($_POST['themesettingtyposhufysizeeight']),
                                                                                    'themesettingtyposhufysizenigne' => (string) $menu->input($_POST['themesettingtyposhufysizenigne']),
                                                                                    'themesettingtyposhufysizeteen' => (string) $menu->input($_POST['themesettingtyposhufysizeteen']),
                                                                                    'themesettingtyposhufysizeeleven' => (string) $menu->input($_POST['themesettingtyposhufysizeeleven']),
                                                                                    'themesettingtyposhufysizetwelve' => (string) $menu->input($_POST['themesettingtyposhufysizetwelve']),
                                                                                    'themesettingtyposhufysizetherteen' => (string) $menu->input($_POST['themesettingtyposhufysizetherteen']),
                                                                                    'themesettingtypohone' => (string) $menu->input($_POST['themesettingtypohone']),
                                                                                    'themesettingtypohtwo' => (string) $menu->input($_POST['themesettingtypohtwo']),
                                                                                    'themesettingtypohthree' => (string) $menu->input($_POST['themesettingtypohthree']),
                                                                                    'themesettingtypohfour' => (string) $menu->input($_POST['themesettingtypohfour']),
                                                                                    'themesettingtypohfive' => (string) $menu->input($_POST['themesettingtypohfive']),
                                                                                    'themesettingtypohsix' => (string) $menu->input($_POST['themesettingtypohsix']),
                                                                                    'themesettingtypop' => (string) $menu->input($_POST['themesettingtypop']),
                                                                                    'themesettingtypobutton' => (string) $menu->input($_POST['themesettingtypobutton']),
                                                                                    'themesettingtyposbutton' => (string) $menu->input($_POST['themesettingtyposbutton']),
                                                                                ]);
                                                                                try {
                                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=typpoptions&success=1', ['message' => 'Shufytheme typography settings have been saved successfully.']);
                                                                                } catch (\Exception $e) {
                                                                                    exit('Error: ' . $e->getMessage());
                                                                                }
                                                                            } else {
                                                                                if ($action == 'resettyppoptions') {
                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                    $filePath1 = ROOTDIR . '/modules/addons/shufyTheme/css-values/typographie.css';
                                                                                    file_put_contents($filePath1, '');
                                                                                    $tableName = 'coodiv__control__typography__settings';
                                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                                    $updateData = array_fill_keys($columns, '');
                                                                                    Manager::table($tableName)->update($updateData);
                                                                                    $menu->redirect(MODURL . '&action=typpoptions&success=1');
                                                                                    try {
                                                                                        exit;
                                                                                    } catch (\Exception $e) {
                                                                                        exit('Error: ' . $e->getMessage());
                                                                                    }
                                                                                } else {
                                                                                    if ($action == 'exporttyppoptions') {
                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                        $themeOptionData = Manager::table('coodiv__control__typography__settings')->get();
                                                                                        $csvData = [];
                                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                                        foreach ($themeOptionData as $row) {
                                                                                            $csvData[] = (array) $row;
                                                                                        }
                                                                                        $csvContent = implode("\n", array_map(function ($version) {
                                                                                            $parts = explode('.', $version);
                                                                                            while (count($parts) < 3) {
                                                                                                $parts[] = 0;
                                                                                            }
                                                                                            $parts[2] = (int) $parts[2] + 1;
                                                                                            return implode('.', $parts);
                                                                                        }, $csvData));
                                                                                        header('Content-Type: text/csv');
                                                                                        header('Content-Disposition: attachment; filename="shufytheme_typography_exported_data.csv"');
                                                                                        echo $csvContent;
                                                                                        try {
                                                                                            exit;
                                                                                        } catch (\Exception $e) {
                                                                                            exit('Error: ' . $e->getMessage());
                                                                                        }
                                                                                    } else {
                                                                                        if ($action == 'importtyppoptions') {
                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                                $columns = array_shift($csvData);
                                                                                                $validData = true;
                                                                                                $invalidRow = null;
                                                                                                foreach ($csvData as $index => $row) {
                                                                                                    if (count($row) !== count($columns)) {
                                                                                                        $validData = false;
                                                                                                        $invalidRow = $index + 1;
                                                                                                        break;
                                                                                                    }
                                                                                                }
                                                                                                if ($validData) {
                                                                                                    Manager::table('coodiv__control__typography__settings')->truncate();
                                                                                                    foreach ($csvData as $row) {
                                                                                                        $data = array_combine($columns, $row);
                                                                                                        Manager::table('coodiv__control__typography__settings')->insert($data);
                                                                                                    }
                                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                                    $menu->redirect(MODURL . '&action=typpoptions&success=1');
                                                                                                    exit;
                                                                                                } else {
                                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                                }
                                                                                            } else {
                                                                                                echo 'Error uploading file.';
                                                                                            }
                                                                                            try {
                                                                                                exit;
                                                                                            } catch (\Exception $e) {
                                                                                                exit('Error: ' . $e->getMessage());
                                                                                            }
                                                                                        } else {
                                                                                            if ($action == 'layoutoptions') {
                                                                                                $themesettingid = '1';
                                                                                                $smarty->assign('themesettingid', $themesettingid);
                                                                                                $getItemInfo = Manager::table('coodiv__control__layout__settings')->where('id', $themesettingid)->get();
                                                                                                $themesetting = $menu->fromMYSQL($getItemInfo);
                                                                                                $smarty->assign('themelayoutsetting', $themesetting[0] ?? []);
                                                                                                $templateFile = 'layoutoptions.tpl';
                                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme Layouts settings');
                                                                                            } elseif ($action == 'applylayoutoptions') {
                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                Manager::statement('TRUNCATE TABLE coodiv__control__layout__settings');
                                                                                                $groupid = Manager::table('coodiv__control__layout__settings')->insertGetId([
                                                                                                    'layoutsettingssidebarlayout' => (string) $menu->input($_POST['layoutsettingssidebarlayout']),
                                                                                                    'layoutsettingssidebarposition' => (string) $menu->input($_POST['layoutsettingssidebarposition']),
                                                                                                    'layoutsettingssidebarstyle' => (string) $menu->input($_POST['layoutsettingssidebarstyle']),
                                                                                                ]);
                                                                                                try {
                                                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=layoutoptions&success=1', ['message' => 'Shufytheme layout settings have been saved successfully.']);
                                                                                                } catch (\Exception $e) {
                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                }
                                                                                            } else {
                                                                                                if ($action == 'resetlayoutoptions') {
                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                    $tableName = 'coodiv__control__layout__settings';
                                                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                                                    $updateData = array_fill_keys($columns, '');
                                                                                                    Manager::table($tableName)->update($updateData);
                                                                                                    $menu->redirect(MODURL . '&action=layoutoptions&success=1');
                                                                                                    try {
                                                                                                        exit;
                                                                                                    } catch (\Exception $e) {
                                                                                                        exit('Error: ' . $e->getMessage());
                                                                                                    }
                                                                                                } else {
                                                                                                    if ($action == 'exportlayoutoptions') {
                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                        $themeOptionData = Manager::table('coodiv__control__layout__settings')->get();
                                                                                                        $csvData = [];
                                                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                                                        foreach ($themeOptionData as $row) {
                                                                                                            $csvData[] = (array) $row;
                                                                                                        }
                                                                                                        $csvContent = implode("\n", array_map(function ($row) {
                                                                                                            return implode(',', $row);
                                                                                                        }, $csvData));
                                                                                                        header('Content-Type: text/csv');
                                                                                                        header('Content-Disposition: attachment; filename="shufytheme_layout_exported_data.csv"');
                                                                                                        echo $csvContent;
                                                                                                        try {
                                                                                                            exit;
                                                                                                        } catch (\Exception $e) {
                                                                                                            exit('Error: ' . $e->getMessage());
                                                                                                        }
                                                                                                    } else {
                                                                                                        if ($action == 'importlayoutoptions') {
                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                                                $columns = array_shift($csvData);
                                                                                                                $validData = true;
                                                                                                                $invalidRow = null;
                                                                                                                foreach ($csvData as $index => $row) {
                                                                                                                    if (count($row) !== count($columns)) {
                                                                                                                        $validData = false;
                                                                                                                        $invalidRow = $index + 1;
                                                                                                                        break;
                                                                                                                    }
                                                                                                                }
                                                                                                                if ($validData) {
                                                                                                                    Manager::table('coodiv__control__layout__settings')->truncate();
                                                                                                                    foreach ($csvData as $row) {
                                                                                                                        $data = array_combine($columns, $row);
                                                                                                                        Manager::table('coodiv__control__layout__settings')->insert($data);
                                                                                                                    }
                                                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                                                    $menu->redirect(MODURL . '&action=layoutoptions&success=1');
                                                                                                                    exit;
                                                                                                                } else {
                                                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                                                }
                                                                                                            } else {
                                                                                                                echo 'Error uploading file.';
                                                                                                            }
                                                                                                            try {
                                                                                                                exit;
                                                                                                            } catch (\Exception $e) {
                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                            }
                                                                                                        } else {
                                                                                                            if ($action == 'sidebaroptions') {
                                                                                                                $themesettingid = '1';
                                                                                                                $smarty->assign('themesettingid', $themesettingid);
                                                                                                                $getItemInfo = Manager::table('coodiv__control__sidebar__settings')->where('id', $themesettingid)->get();
                                                                                                                $themesetting = $menu->fromMYSQL($getItemInfo);
                                                                                                                $smarty->assign('themesidebarsetting', $themesetting[0] ?? []);
                                                                                                                $templateFile = 'sidebaroptions.tpl';
                                                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme Sidebar settings');
                                                                                                            } elseif ($action == 'applysidebaroptions') {
                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                Manager::statement('TRUNCATE TABLE coodiv__control__sidebar__settings');
                                                                                                                $groupid = Manager::table('coodiv__control__sidebar__settings')->insertGetId([
                                                                                                                    'themesidebarsettingsdarkmode' => (string) $menu->input($_POST['themesidebarsettingsdarkmode']),
                                                                                                                    'themesidebarsettingscollapsed' => (string) $menu->input($_POST['themesidebarsettingscollapsed']),
                                                                                                                    'themesidebarsettingsallowusertoexpend' => (string) $menu->input($_POST['themesidebarsettingsallowusertoexpend']),
                                                                                                                    'themesidebarsettingsallowusertocollapse' => (string) $menu->input($_POST['themesidebarsettingsallowusertocollapse']),
                                                                                                                    'themesidebarsettingsfixedtopheader' => (string) $menu->input($_POST['themesidebarsettingsfixedtopheader']),
                                                                                                                    'themesidebarsettingsfixedhorizontalmenu' => (string) $menu->input($_POST['themesidebarsettingsfixedhorizontalmenu']),
                                                                                                                    'themesidebarsettingsfixedsecondarymenu' => (string) $menu->input($_POST['themesidebarsettingsfixedsecondarymenu']),
                                                                                                                    'themesidebarsettingssidebaronhover' => (string) $menu->input($_POST['themesidebarsettingssidebaronhover']),
                                                                                                                    'themesidebarsettingschildonhover' => (string) $menu->input($_POST['themesidebarsettingschildonhover']),
                                                                                                                    'themesidebarsettingsdarkicons' => (string) $menu->input($_POST['themesidebarsettingsdarkicons']),
                                                                                                                    'themesidebarsettingswithouticons' => (string) $menu->input($_POST['themesidebarsettingswithouticons']),
                                                                                                                    'themesidebarsettingfullwidthtopheader' => (string) $menu->input($_POST['themesidebarsettingfullwidthtopheader']),
                                                                                                                    'themesidebarsettingfullwithhorizontalmenu' => (string) $menu->input($_POST['themesidebarsettingfullwithhorizontalmenu']),
                                                                                                                ]);
                                                                                                                try {
                                                                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=sidebaroptions&success=1', ['message' => 'Shufytheme sidebar settings have been saved successfully.']);
                                                                                                                } catch (\Exception $e) {
                                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                                }
                                                                                                            } else {
                                                                                                                if ($action == 'resetsidebaroptions') {
                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                    $tableName = 'coodiv__control__sidebar__settings';
                                                                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                                                                    $updateData = array_fill_keys($columns, '');
                                                                                                                    Manager::table($tableName)->update($updateData);
                                                                                                                    $menu->redirect(MODURL . '&action=sidebaroptions&success=1');
                                                                                                                    try {
                                                                                                                        exit;
                                                                                                                    } catch (\Exception $e) {
                                                                                                                        exit('Error: ' . $e->getMessage());
                                                                                                                    }
                                                                                                                } else {
                                                                                                                    if ($action == 'exportsidebaroptions') {
                                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                        $themeOptionData = Manager::table('coodiv__control__sidebar__settings')->get();
                                                                                                                        $csvData = [];
                                                                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                                                                        foreach ($themeOptionData as $row) {
                                                                                                                            $csvData[] = (array) $row;
                                                                                                                        }
                                                                                                                        $csvContent = implode("\n", array_map(function ($row) {
                                                                                                                            return implode(',', $row);
                                                                                                                        }, $csvData));
                                                                                                                        header('Content-Type: text/csv');
                                                                                                                        header('Content-Disposition: attachment; filename="shufytheme_sidebar_exported_data.csv"');
                                                                                                                        echo $csvContent;
                                                                                                                        try {
                                                                                                                            exit;
                                                                                                                        } catch (\Exception $e) {
                                                                                                                            exit('Error: ' . $e->getMessage());
                                                                                                                        }
                                                                                                                    } else {
                                                                                                                        if ($action == 'importsidebaroptions') {
                                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                                                                $columns = array_shift($csvData);
                                                                                                                                $validData = true;
                                                                                                                                $invalidRow = null;
                                                                                                                                foreach ($csvData as $index => $row) {
                                                                                                                                    if (count($row) !== count($columns)) {
                                                                                                                                        $validData = false;
                                                                                                                                        $invalidRow = $index + 1;
                                                                                                                                        break;
                                                                                                                                    }
                                                                                                                                }
                                                                                                                                if ($validData) {
                                                                                                                                    Manager::table('coodiv__control__sidebar__settings')->truncate();
                                                                                                                                    foreach ($csvData as $row) {
                                                                                                                                        $data = array_combine($columns, $row);
                                                                                                                                        Manager::table('coodiv__control__sidebar__settings')->insert($data);
                                                                                                                                    }
                                                                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                                                                    $menu->redirect(MODURL . '&action=sidebaroptions&success=1');
                                                                                                                                    exit;
                                                                                                                                } else {
                                                                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                                                                }
                                                                                                                            } else {
                                                                                                                                echo 'Error uploading file.';
                                                                                                                            }
                                                                                                                            try {
                                                                                                                                exit;
                                                                                                                            } catch (\Exception $e) {
                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                            }
                                                                                                                        } else {
                                                                                                                            if ($action == 'footeroptions') {
                                                                                                                                $themesettingid = '1';
                                                                                                                                $smarty->assign('themesettingid', $themesettingid);
                                                                                                                                $getItemInfo = Manager::table('coodiv__control__footer__settings')->where('id', $themesettingid)->get();
                                                                                                                                $themesetting = $menu->fromMYSQL($getItemInfo);
                                                                                                                                $smarty->assign('themefootersetting', $themesetting[0] ?? []);
                                                                                                                                $templateFile = 'footeroptions.tpl';
                                                                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme footer settings');
                                                                                                                            } elseif ($action == 'applyfooteroptions') {
                                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                Manager::statement('TRUNCATE TABLE coodiv__control__footer__settings');
                                                                                                                                $groupid = Manager::table('coodiv__control__footer__settings')->insertGetId([
                                                                                                                                    'themefootersettingstyle' => (string) $menu->input($_POST['themefootersettingstyle']),
                                                                                                                                    'themefootersettingpoworedbycoodiv' => (string) $menu->input($_POST['themefootersettingpoworedbycoodiv']),
                                                                                                                                    'themefootersettinglogo' => (string) $menu->input($_POST['themefootersettinglogo']),
                                                                                                                                    'themefootersettingdescription' => (string) $menu->input($_POST['themefootersettingdescription']),
                                                                                                                                    'themefootersettingsocialicons' => (string) $menu->input($_POST['themefootersettingsocialicons']),
                                                                                                                                    'themefootersettingadress' => (string) $menu->input($_POST['themefootersettingadress']),
                                                                                                                                    'themefootersettingmobile' => (string) $menu->input($_POST['themefootersettingmobile']),
                                                                                                                                    'themefootersettingemail' => (string) $menu->input($_POST['themefootersettingemail']),
                                                                                                                                    'themefootersettingcustommobile' => (string) $menu->input($_POST['themefootersettingcustommobile']),
                                                                                                                                    'themefootersettingcustomemail' => (string) $menu->input($_POST['themefootersettingcustomemail']),
                                                                                                                                    'accordionfootermenu' => (string) $menu->input($_POST['accordionfootermenu']),
                                                                                                                                    'themefootersettingcustomcopyrighttext' => (string) $menu->input($_POST['themefootersettingcustomcopyrighttext']),
                                                                                                                                ]);
                                                                                                                                try {
                                                                                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=footeroptions&success=1', ['message' => 'Shufytheme footer settings have been saved successfully.']);
                                                                                                                                } catch (\Exception $e) {
                                                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                                                }
                                                                                                                            } else {
                                                                                                                                if ($action == 'resetfooteroptions') {
                                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                    $tableName = 'coodiv__control__footer__settings';
                                                                                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                                                                                    $updateData = array_fill_keys($columns, '');
                                                                                                                                    Manager::table($tableName)->update($updateData);
                                                                                                                                    $menu->redirect(MODURL . '&action=footeroptions&success=1');
                                                                                                                                    try {
                                                                                                                                        exit;
                                                                                                                                    } catch (\Exception $e) {
                                                                                                                                        exit('Error: ' . $e->getMessage());
                                                                                                                                    }
                                                                                                                                } else {
                                                                                                                                    if ($action == 'exportfooteroptions') {
                                                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                        $themeOptionData = Manager::table('coodiv__control__footer__settings')->get();
                                                                                                                                        $csvData = [];
                                                                                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                                                                                        foreach ($themeOptionData as $row) {
                                                                                                                                            $csvData[] = (array) $row;
                                                                                                                                        }
                                                                                                                                        $csvContent = implode("\n", array_map(function ($row) {
                                                                                                                                            return implode(',', $row);
                                                                                                                                        }, $csvData));
                                                                                                                                        header('Content-Type: text/csv');
                                                                                                                                        header('Content-Disposition: attachment; filename="shufytheme_footer_exported_data.csv"');
                                                                                                                                        echo $csvContent;
                                                                                                                                        try {
                                                                                                                                            exit;
                                                                                                                                        } catch (\Exception $e) {
                                                                                                                                            exit('Error: ' . $e->getMessage());
                                                                                                                                        }
                                                                                                                                    } else {
                                                                                                                                        if ($action == 'importfooteroptions') {
                                                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                                                                                $columns = array_shift($csvData);
                                                                                                                                                $validData = true;
                                                                                                                                                $invalidRow = null;
                                                                                                                                                foreach ($csvData as $index => $row) {
                                                                                                                                                    if (count($row) !== count($columns)) {
                                                                                                                                                        $validData = false;
                                                                                                                                                        $invalidRow = $index + 1;
                                                                                                                                                        break;
                                                                                                                                                    }
                                                                                                                                                }
                                                                                                                                                if ($validData) {
                                                                                                                                                    Manager::table('coodiv__control__footer__settings')->truncate();
                                                                                                                                                    foreach ($csvData as $row) {
                                                                                                                                                        $data = array_combine($columns, $row);
                                                                                                                                                        Manager::table('coodiv__control__footer__settings')->insert($data);
                                                                                                                                                    }
                                                                                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                                                                                    $menu->redirect(MODURL . '&action=footeroptions&success=1');
                                                                                                                                                    exit;
                                                                                                                                                } else {
                                                                                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                                                                                }
                                                                                                                                            } else {
                                                                                                                                                echo 'Error uploading file.';
                                                                                                                                            }
                                                                                                                                            try {
                                                                                                                                                exit;
                                                                                                                                            } catch (\Exception $e) {
                                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                                            }
                                                                                                                                        } else {
                                                                                                                                            if ($action == 'homepageoptions') {
                                                                                                                                                $themesettingid = '1';
                                                                                                                                                $smarty->assign('themesettingid', $themesettingid);
                                                                                                                                                $getItemInfo = Manager::table('coodiv__control__homepage__settings')->where('id', $themesettingid)->get();
                                                                                                                                                $themesetting = $menu->fromMYSQL($getItemInfo);
                                                                                                                                                $smarty->assign('themehomepagesetting', $themesetting[0] ?? []);
                                                                                                                                                $templateFile = 'homepageoptions.tpl';
                                                                                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme Homepage settings');
                                                                                                                                            } elseif ($action == 'applyhomepageoptions') {
                                                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                if ($_SERVER['REQUEST_METHOD'] === 'POST') {
                                                                                                                                                    $data1 = $_POST['themehomepagesettingfeaturescolorsplansfirstbg'];
                                                                                                                                                    $data2 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtnbg'];
                                                                                                                                                    $data3 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtncolor'];
                                                                                                                                                    $data4 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtnhover'];
                                                                                                                                                    $data5 = $_POST['themehomepagesettingfeaturescolorsplansfirstbgdark'];
                                                                                                                                                    $data6 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtnbgdark'];
                                                                                                                                                    $data7 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtncolordark'];
                                                                                                                                                    $data8 = $_POST['themehomepagesettingfeaturescolorsplansfirstbtnbgdarkhover'];
                                                                                                                                                    $data9 = $_POST['themehomepagesettingfeaturescolorsplanssecondbg'];
                                                                                                                                                    $data10 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtnbg'];
                                                                                                                                                    $data11 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtncolor'];
                                                                                                                                                    $data12 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtnhover'];
                                                                                                                                                    $data13 = $_POST['themehomepagesettingfeaturescolorsplanssecondbgdark'];
                                                                                                                                                    $data14 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtnbgdark'];
                                                                                                                                                    $data15 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtncolordark'];
                                                                                                                                                    $data16 = $_POST['themehomepagesettingfeaturescolorsplanssecondbtnbgdarkhover'];
                                                                                                                                                    $data17 = $_POST['themehomepagesettingfeaturescolorsplansthirdbg'];
                                                                                                                                                    $data18 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtnbg'];
                                                                                                                                                    $data19 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtncolor'];
                                                                                                                                                    $data20 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtnhover'];
                                                                                                                                                    $data21 = $_POST['themehomepagesettingfeaturescolorsplansthirdbgdark'];
                                                                                                                                                    $data22 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtnbgdark'];
                                                                                                                                                    $data23 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtncolordark'];
                                                                                                                                                    $data24 = $_POST['themehomepagesettingfeaturescolorsplansthirdbtnbgdarkhover'];
                                                                                                                                                    $header = ':root{';
                                                                                                                                                    $footer = '}';
                                                                                                                                                    $titles = [
                                                                                                                                                        '--first-homepage-plan-bg',
                                                                                                                                                        '--first-homepage-plan-btn-bg',
                                                                                                                                                        '--first-homepage-plan-btn-color',
                                                                                                                                                        '--first-homepage-plan-btn-hover',
                                                                                                                                                        '--first-homepage-plan-bg-dark',
                                                                                                                                                        '--first-homepage-plan-btn-bg-dark',
                                                                                                                                                        '--first-homepage-plan-btn-color-dark',
                                                                                                                                                        '--first-homepage-plan-btn-hover-dark',
                                                                                                                                                        '--second-homepage-plan-bg',
                                                                                                                                                        '--second-homepage-plan-btn-bg',
                                                                                                                                                        '--second-homepage-plan-btn-color',
                                                                                                                                                        '--second-homepage-plan-btn-hover',
                                                                                                                                                        '--second-homepage-plan-bg-dark',
                                                                                                                                                        '--second-homepage-plan-btn-bg-dark',
                                                                                                                                                        '--second-homepage-plan-btn-color-dark',
                                                                                                                                                        '--second-homepage-plan-btn-hover-dark',
                                                                                                                                                        '--third-homepage-plan-bg',
                                                                                                                                                        '--third-homepage-plan-btn-bg',
                                                                                                                                                        '--third-homepage-plan-btn-color',
                                                                                                                                                        '--third-homepage-plan-btn-hover',
                                                                                                                                                        '--third-homepage-plan-bg-dark',
                                                                                                                                                        '--third-homepage-plan-btn-bg-dark',
                                                                                                                                                        '--third-homepage-plan-btn-color-dark',
                                                                                                                                                        '--third-homepage-plan-btn-hover-dark',
                                                                                                                                                    ];
                                                                                                                                                    $filePath = ROOTDIR . '/modules/addons/shufyTheme/css-values/homepage-plans.css';
                                                                                                                                                    $file = fopen($filePath, 'w');
                                                                                                                                                    fwrite($file, $header . PHP_EOL);
                                                                                                                                                    $i = 2;
                                                                                                                                                    while ($i < count($titles)) {
                                                                                                                                                        $value = ${'data' . $i + 1};
                                                                                                                                                        if (!empty($value)) {
                                                                                                                                                            fwrite($file, $titles[$i] . ': ' . $value . ';');
                                                                                                                                                        }
                                                                                                                                                        ++$i;
                                                                                                                                                    }
                                                                                                                                                    fwrite($file, $footer . PHP_EOL);
                                                                                                                                                    fclose($file);
                                                                                                                                                }
                                                                                                                                                Manager::statement('TRUNCATE TABLE coodiv__control__homepage__settings');
                                                                                                                                                $groupid = Manager::table('coodiv__control__homepage__settings')->insertGetId([
                                                                                                                                                    'themehomepagesettingstyle' => (string) $menu->input($_POST['themehomepagesettingstyle']),
                                                                                                                                                    'themehomepagesettingmarketconnectbannaers' => (string) $menu->input($_POST['themehomepagesettingmarketconnectbannaers']),
                                                                                                                                                    'themehomepagesettingmarketconnectbannaersnav' => (string) $menu->input($_POST['themehomepagesettingmarketconnectbannaersnav']),
                                                                                                                                                    'themehomepagesettingannouncements' => (string) $menu->input($_POST['themehomepagesettingannouncements']),
                                                                                                                                                    'themehomepagesettinghomepagefeaturedsection' => (string) $menu->input($_POST['themehomepagesettinghomepagefeaturedsection']),
                                                                                                                                                    'themehomepagesettinghomepagefeaturedsectiontitle' => (string) $menu->input($_POST['themehomepagesettinghomepagefeaturedsectiontitle']),
                                                                                                                                                    'themehomepagesettinghomepagefeaturedsectionsubtitle' => (string) $menu->input($_POST['themehomepagesettinghomepagefeaturedsectionsubtitle']),
                                                                                                                                                    'themehomepagesettingfeaturedfirst' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirst']),
                                                                                                                                                    'themehomepagesettingfeaturedssecond' => (string) $menu->input($_POST['themehomepagesettingfeaturedssecond']),
                                                                                                                                                    'themehomepagesettingfeaturedthird' => (string) $menu->input($_POST['themehomepagesettingfeaturedthird']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontenttitle' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontenttitle']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontenttitleicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontenttitleicon']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentsubtitleone' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentsubtitleone']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentsubtitleoneicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentsubtitleoneicon']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentsubtitletwo' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentsubtitletwo']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentsubtitletwoicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentsubtitletwoicon']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentsubtitlethree' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentsubtitlethree']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentprice' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentprice']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentpricebilling' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentpricebilling']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentdescription' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentdescription']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentinllustration' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentinllustration']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentbutton' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentbutton']),
                                                                                                                                                    'themehomepagesettingfeaturedfirstcontentbuttonlink' => (string) $menu->input($_POST['themehomepagesettingfeaturedfirstcontentbuttonlink']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontenttitle' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontenttitle']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontenttitleicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontenttitleicon']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentsubtitleone' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentsubtitleone']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentsubtitleoneicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentsubtitleoneicon']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentsubtitletwo' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentsubtitletwo']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentsubtitletwoicon' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentsubtitletwoicon']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentsubtitlethree' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentsubtitlethree']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentprice' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentprice']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentpricebilling' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentpricebilling']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentdescription' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentdescription']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentinllustration' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentinllustration']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentbutton' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentbutton']),
                                                                                                                                                    'themehomepagesettingfeaturedsecondcontentbuttonlink' => (string) $menu->input($_POST['themehomepagesettingfeaturedsecondcontentbuttonlink']),
                                                                                                                                                    'themehomepagesettingfeatureddomomainsectiontitle' => (string) $menu->input($_POST['themehomepagesettingfeatureddomomainsectiontitle']),
                                                                                                                                                    'themehomepagesettingfeatureddomomainsectionsubtitle' => (string) $menu->input($_POST['themehomepagesettingfeatureddomomainsectionsubtitle']),
                                                                                                                                                    'themehomepagesettingfeatureddomomainsectionsubtitletwo' => (string) $menu->input($_POST['themehomepagesettingfeatureddomomainsectionsubtitletwo']),
                                                                                                                                                    'themehomepagesettingfeatureddomomainsectionsubtitlethree' => (string) $menu->input($_POST['themehomepagesettingfeatureddomomainsectionsubtitlethree']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirst' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirst']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtnbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtnbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtnhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtnhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtncolor' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtncolor']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtnbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtnbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtncolordark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtncolordark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtnbgdarkhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtnbgdarkhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirsticon' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirsticon']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirsttitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirsttitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstsubtitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstsubtitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstdescription' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstdescription']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstprice' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstprice']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbilling' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbilling']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtntext' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtntext']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansfirstbtnlink' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansfirstbtnlink']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecond' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecond']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtnbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtnbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtnhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtnhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtncolor' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtncolor']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtnbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtnbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtncolordark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtncolordark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtnbgdarkhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtnbgdarkhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondicon' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondicon']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondtitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondtitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondsubtitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondsubtitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansseconddescription' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansseconddescription']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondprice' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondprice']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbilling' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbilling']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtntext' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtntext']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplanssecondbtnlink' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplanssecondbtnlink']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthird' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthird']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtnbg' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtnbg']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtnhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtnhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtncolor' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtncolor']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtnbgdark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtnbgdark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtncolordark' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtncolordark']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtnbgdarkhover' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtnbgdarkhover']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdicon' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdicon']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdtitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdtitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdsubtitle' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdsubtitle']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirddescription' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirddescription']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdprice' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdprice']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbilling' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbilling']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtntext' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtntext']),
                                                                                                                                                    'themehomepagesettingfeaturescolorsplansthirdbtnlink' => (string) $menu->input($_POST['themehomepagesettingfeaturescolorsplansthirdbtnlink']),
                                                                                                                                                    'themehomepagesettingservicesfeatures' => (string) $menu->input($_POST['themehomepagesettingservicesfeatures']),
                                                                                                                                                    'themehomepagesettingservicesfeaturestagline' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturestagline']),
                                                                                                                                                    'themehomepagesettingservicesfeaturestitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturestitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturessubtitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturessubtitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturessecond' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturessecond']),
                                                                                                                                                    'themehomepagesettingservicesfeaturessecondicon' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturessecondicon']),
                                                                                                                                                    'themehomepagesettingservicesfeaturessecondtitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturessecondtitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesseconddescription' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesseconddescription']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesthird' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesthird']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesthirdicon' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesthirdicon']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesthirdtitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesthirdtitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesthirddescription' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesthirddescription']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfourth' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfourth']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfourthicon' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfourthicon']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfourthtitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfourthtitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfourthdescription' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfourthdescription']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfivth' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfivth']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfivthicon' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfivthicon']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfivthtitle' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfivthtitle']),
                                                                                                                                                    'themehomepagesettingservicesfeaturesfivthdescription' => (string) $menu->input($_POST['themehomepagesettingservicesfeaturesfivthdescription']),
                                                                                                                                                    'themehomepagesettingsavingbanner' => (string) $menu->input($_POST['themehomepagesettingsavingbanner']),
                                                                                                                                                    'themehomepagesettingsavingbannertitle' => (string) $menu->input($_POST['themehomepagesettingsavingbannertitle']),
                                                                                                                                                    'themehomepagesettingsavingbannersubtitle' => (string) $menu->input($_POST['themehomepagesettingsavingbannersubtitle']),
                                                                                                                                                    'themehomepagesettingsavingbannerbtntext' => (string) $menu->input($_POST['themehomepagesettingsavingbannerbtntext']),
                                                                                                                                                    'themehomepagesettingsavingbannerbtnlink' => (string) $menu->input($_POST['themehomepagesettingsavingbannerbtnlink']),
                                                                                                                                                    'themehomepagesettingsubscribingsection' => (string) $menu->input($_POST['themehomepagesettingsubscribingsection']),
                                                                                                                                                    'themehomepagesettingsubscribingsectiontitle' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectiontitle']),
                                                                                                                                                    'themehomepagesettingsubscribingsectionsubtitle' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectionsubtitle']),
                                                                                                                                                    'themehomepagesettingsubscribingsectionmailchimpusername' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectionmailchimpusername']),
                                                                                                                                                    'themehomepagesettingsubscribingsectionmailchimapi' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectionmailchimapi']),
                                                                                                                                                    'themehomepagesettingsubscribingsectionmailchimcode' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectionmailchimcode']),
                                                                                                                                                    'themehomepagesettingsubscribingsectionmailchimoption' => (string) $menu->input($_POST['themehomepagesettingsubscribingsectionmailchimoption']),
                                                                                                                                                ]);
                                                                                                                                                try {
                                                                                                                                                    shufyTheme_ajax_or_redirect($menu, MODURL . '&action=homepageoptions&success=1', ['message' => 'Shufytheme homepage settings have been saved successfully.']);
                                                                                                                                                } catch (\Exception $e) {
                                                                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                                                                }
                                                                                                                                            } else {
                                                                                                                                                if ($action == 'resethomepageptions') {
                                                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                    $filePath1 = ROOTDIR . '/modules/addons/shufyTheme/css-values/homepage-plans.css';
                                                                                                                                                    file_put_contents($filePath1, '');
                                                                                                                                                    $tableName = 'coodiv__control__homepage__settings';
                                                                                                                                                    $columns = Manager::schema()->getColumnListing($tableName);
                                                                                                                                                    $updateData = array_fill_keys($columns, '');
                                                                                                                                                    Manager::table($tableName)->update($updateData);
                                                                                                                                                    $menu->redirect(MODURL . '&action=homepageoptions&success=1');
                                                                                                                                                    try {
                                                                                                                                                        exit;
                                                                                                                                                    } catch (\Exception $e) {
                                                                                                                                                        exit('Error: ' . $e->getMessage());
                                                                                                                                                    }
                                                                                                                                                } else {
                                                                                                                                                    if ($action == 'exporthomepageptions') {
                                                                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                        $themeOptionData = Manager::table('coodiv__control__homepage__settings')->get();
                                                                                                                                                        $csvData = [];
                                                                                                                                                        $csvData[] = array_keys((array) $themeOptionData->first());
                                                                                                                                                        foreach ($themeOptionData as $row) {
                                                                                                                                                            $csvData[] = (array) $row;
                                                                                                                                                        }
                                                                                                                                                        $csvContent = implode("\n", array_map(function ($row) {
                                                                                                                                                            return implode(',', $row);
                                                                                                                                                        }, $csvData));
                                                                                                                                                        header('Content-Type: text/csv');
                                                                                                                                                        header('Content-Disposition: attachment; filename="shufytheme_homepage_exported_data.csv"');
                                                                                                                                                        echo $csvContent;
                                                                                                                                                        try {
                                                                                                                                                            exit;
                                                                                                                                                        } catch (\Exception $e) {
                                                                                                                                                            exit('Error: ' . $e->getMessage());
                                                                                                                                                        }
                                                                                                                                                    } else {
                                                                                                                                                        if ($action == 'importhomepageptions') {
                                                                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                            if ($_FILES['uploaded_file']['error'] == UPLOAD_ERR_OK) {
                                                                                                                                                                $csvContent = file_get_contents($_FILES['uploaded_file']['tmp_name']);
                                                                                                                                                                $csvData = array_map('str_getcsv', explode("\n", $csvContent));
                                                                                                                                                                $columns = array_shift($csvData);
                                                                                                                                                                $validData = true;
                                                                                                                                                                $invalidRow = null;
                                                                                                                                                                foreach ($csvData as $index => $row) {
                                                                                                                                                                    if (count($row) !== count($columns)) {
                                                                                                                                                                        $validData = false;
                                                                                                                                                                        $invalidRow = $index + 1;
                                                                                                                                                                        break;
                                                                                                                                                                    }
                                                                                                                                                                }
                                                                                                                                                                if ($validData) {
                                                                                                                                                                    Manager::table('coodiv__control__homepage__settings')->truncate();
                                                                                                                                                                    foreach ($csvData as $row) {
                                                                                                                                                                        $data = array_combine($columns, $row);
                                                                                                                                                                        Manager::table('coodiv__control__homepage__settings')->insert($data);
                                                                                                                                                                    }
                                                                                                                                                                    echo 'Upload successful! Data has been overwritten.';
                                                                                                                                                                    $menu->redirect(MODURL . '&action=homepageoptions&success=1');
                                                                                                                                                                    exit;
                                                                                                                                                                } else {
                                                                                                                                                                    echo 'Error: Rows in the CSV file have different lengths. Invalid row: ' . $invalidRow;
                                                                                                                                                                }
                                                                                                                                                            } else {
                                                                                                                                                                echo 'Error uploading file.';
                                                                                                                                                            }
                                                                                                                                                            try {
                                                                                                                                                                exit;
                                                                                                                                                            } catch (\Exception $e) {
                                                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                                                            }
                                                                                                                                                        } else {
                                                                                                                                                            if ($action == 'listgroup') {
                                                                                                                                                                include ROOTDIR . '/modules/addons/shufyTheme/classes/templates.class.php';
                                                                                                                                                                $smarty->assign('compatibletemplates', $supportedTemplates);
                                                                                                                                                                $getGroups = Manager::table('coodiv__control__panel__table')->orderBy('id', 'desc')->get();
                                                                                                                                                                $groups = $menu->fromMYSQL($getGroups);
                                                                                                                                                                $smarty->assign('groups', $groups);
                                                                                                                                                                $menu->addToBreadCrumbs('', 'Shufy Theme Menu manager');
                                                                                                                                                            } elseif ($action == 'lisence') {
                                                                                                                                                                if ($licenseactivated) {
                                                                                                                                                                    $menu->redirect(MODURL . '&action="homepage"');
                                                                                                                                                                } elseif (isset($_POST['purchase_code'])) {
                                                                                                                                                                    $purchase_code = htmlspecialchars($_POST['purchase_code']);
                                                                                                                                                                    $o = EnvatoApi2::verifyPurchase($purchase_code);
                                                                                                                                                                    if (is_object($o)) {
                                                                                                                                                                        $website = parse_url($_SERVER['HTTP_REFERER'], PHP_URL_HOST);
                                                                                                                                                                        $searchformUrl = 'https://demo.coodiv.net/shufytheme/purchases-verify/purchase_search.php';
                                                                                                                                                                        $searchformData = ['purchase_code' => $purchase_code, 'purchase_website' => $website];
                                                                                                                                                                        $search = curl_init($searchformUrl);
                                                                                                                                                                        curl_setopt($search, CURLOPT_POST, 1);
                                                                                                                                                                        curl_setopt($search, CURLOPT_POSTFIELDS, $searchformData);
                                                                                                                                                                        curl_setopt($search, CURLOPT_RETURNTRANSFER, true);
                                                                                                                                                                        $response = curl_exec($search);
                                                                                                                                                                        curl_close($search);
                                                                                                                                                                        $searchResult = json_decode($response, true);
                                                                                                                                                                        if ($searchResult['purchase_found']) {
                                                                                                                                                                            $license__check__pages = 'usedlicense.tpl';
                                                                                                                                                                        } else {
                                                                                                                                                                            Manager::statement('TRUNCATE TABLE coodiv__control__panel__license');
                                                                                                                                                                            Manager::table('coodiv__control__panel__license')->insertGetId([
                                                                                                                                                                                'coodivliecense' => (string) $menu->input($_POST['purchase_code']),
                                                                                                                                                                                'itemname' => (string) $o->item->name,
                                                                                                                                                                                'itemid' => (string) $o->item->id,
                                                                                                                                                                                'itemsoldat' => (string) date('d F Y', strtotime($o->sold_at)),
                                                                                                                                                                                'itembuyer' => (string) $o->buyer,
                                                                                                                                                                                'itemlicense' => (string) $o->license,
                                                                                                                                                                                'itemsupported' => (string) date('d F Y', strtotime($o->supported_until)),
                                                                                                                                                                            ]);
                                                                                                                                                                            try {
                                                                                                                                                                                $menu->redirect(MODURL . '&action="homepage&success=1"');
                                                                                                                                                                            } catch (\Exception $e) {
                                                                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                                                                            }
                                                                                                                                                                            $formUrl = 'https://demo.coodiv.net/shufytheme/purchases-verify/send-lisence.php';
                                                                                                                                                                            $formData = [
                                                                                                                                                                                'verification_date' => date('d F Y'),
                                                                                                                                                                                'purchase_code' => $purchase_code,
                                                                                                                                                                                'purchase_website' => $website,
                                                                                                                                                                            ];
                                                                                                                                                                            $ch = curl_init($formUrl);
                                                                                                                                                                            curl_setopt($ch, CURLOPT_POST, 1);
                                                                                                                                                                            curl_setopt($ch, CURLOPT_POSTFIELDS, $formData);
                                                                                                                                                                            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                                                                                                                                                                            $response = curl_exec($ch);
                                                                                                                                                                            curl_close($ch);
                                                                                                                                                                        }
                                                                                                                                                                    } else {
                                                                                                                                                                        $license__check__pages = 'errorlicense.tpl';
                                                                                                                                                                    }
                                                                                                                                                                }
                                                                                                                                                            } else {
                                                                                                                                                                if ($action == 'addnewgroup') {
                                                                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                    $templateFile = 'addnewgroup.tpl';
                                                                                                                                                                    include ROOTDIR . '/modules/addons/shufyTheme/classes/templates.class.php';
                                                                                                                                                                    $smarty->assign('compatibletemplates', $supportedTemplates);
                                                                                                                                                                    $getGroups = Manager::table('coodiv__control__panel__table')->orderBy('id', 'desc')->get();
                                                                                                                                                                    $groups = $menu->fromMYSQL($getGroups);
                                                                                                                                                                    $smarty->assign('groups', $groups);
                                                                                                                                                                    $menu->addToBreadCrumbs(MODURL . '&action=listgroup', 'Shufy Theme Menu manager');
                                                                                                                                                                    $menu->addToBreadCrumbs('', 'Create new menus group');
                                                                                                                                                                } elseif ($action == 'createdefaultwhmcsmenu') {
                                                                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
                                                                                                                                                                        $menu->redirect(MODURL . '&action=listgroup');
                                                                                                                                                                        exit;
                                                                                                                                                                    }
                                                                                                                                                                    include ROOTDIR . '/modules/addons/shufyTheme/classes/templates.class.php';
                                                                                                                                                                    $templateKey = 'emyui';
                                                                                                                                                                    if (!isset($supportedTemplates[$templateKey])) {
                                                                                                                                                                        $templateKeys = array_keys($supportedTemplates);
                                                                                                                                                                        $templateKey = $templateKeys[0] ?? '';
                                                                                                                                                                    }
                                                                                                                                                                    $groupid = 2;
                                                                                                                                                                    $groupName = shufyTheme_get_unique_menu_group_name('Default WHMCS Menu');
                                                                                                                                                                    $groupid = Manager::table('coodiv__control__panel__table')->insertGetId([
                                                                                                                                                                        'name' => $groupName,
                                                                                                                                                                        'template' => (string) $templateKey,
                                                                                                                                                                        'css_activeclass' => 'active',
                                                                                                                                                                        'isprimary' => 0,
                                                                                                                                                                        'issecondary' => 0,
                                                                                                                                                                    ]);
                                                                                                                                                                    $menu->installWHMCSPrimaryNavbar($groupid);
                                                                                                                                                                    shufyTheme_normalize_menu_group_url_types($groupid);
                                                                                                                                                                    $menu->redirect(MODURL . '&action=listitems&groupid=' . $groupid . '&success=1&defaultmenu=1');
                                                                                                                                                                    exit;
                                                                                                                                                                    goto label_10909;
                                                                                                                                                                    if (0 < $groupid) {
                                                                                                                                                                        Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->delete();
                                                                                                                                                                        Manager::table('coodiv__control__panel__table')->where('id', $groupid)->delete();
                                                                                                                                                                    }
                                                                                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                                                                                } else {
                                                                                                                                                                    label_10909:
                                                                                                                                                                    if ($action == 'createdemofootermenu') {
                                                                                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
                                                                                                                                                                            $menu->redirect(MODURL . '&action=listgroup');
                                                                                                                                                                            exit;
                                                                                                                                                                        }
                                                                                                                                                                        include ROOTDIR . '/modules/addons/shufyTheme/classes/templates.class.php';
                                                                                                                                                                        $templateKey = 'emyui';
                                                                                                                                                                        if (!isset($supportedTemplates[$templateKey])) {
                                                                                                                                                                            $templateKeys = array_keys($supportedTemplates);
                                                                                                                                                                            $templateKey = $templateKeys[0] ?? '';
                                                                                                                                                                        }
                                                                                                                                                                        $groupid = 2;
                                                                                                                                                                        $groupName = shufyTheme_get_unique_menu_group_name('Demo Footer Menu');
                                                                                                                                                                        $groupid = Manager::table('coodiv__control__panel__table')->insertGetId([
                                                                                                                                                                            'name' => $groupName,
                                                                                                                                                                            'template' => (string) $templateKey,
                                                                                                                                                                            'css_activeclass' => 'active',
                                                                                                                                                                            'isprimary' => 0,
                                                                                                                                                                            'issecondary' => 0,
                                                                                                                                                                        ]);
                                                                                                                                                                        $defaultLanguage = strtolower($CONFIG['Language']);
                                                                                                                                                                        $now = date('Y-m-d H:i:s');
                                                                                                                                                                        $footerMenus = [
                                                                                                                                                                            [
                                                                                                                                                                                'title' => 'Company',
                                                                                                                                                                                'children' => [
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Announcements',
                                                                                                                                                                                        'url' => 'announcements.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    ['title' => 'Contact Us', 'url' => 'contact.php', 'urltype' => 'clientarea-off'],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Affiliates',
                                                                                                                                                                                        'url' => 'affiliates.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                ],
                                                                                                                                                                            ],
                                                                                                                                                                            [
                                                                                                                                                                                'title' => 'Services',
                                                                                                                                                                                'children' => [
                                                                                                                                                                                    ['title' => 'Order', 'url' => 'cart.php', 'urltype' => 'clientarea-off'],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Register a New Domain',
                                                                                                                                                                                        'url' => 'cart.php?a=add&domain=register',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Transfer Domains to Us',
                                                                                                                                                                                        'url' => 'cart.php?a=add&domain=transfer',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'View Available Addons',
                                                                                                                                                                                        'url' => 'cart.php?gid=addons',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                ],
                                                                                                                                                                            ],
                                                                                                                                                                            [
                                                                                                                                                                                'title' => 'Support',
                                                                                                                                                                                'children' => [
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Support Tickets',
                                                                                                                                                                                        'url' => 'supporttickets.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Open New Ticket',
                                                                                                                                                                                        'url' => 'submitticket.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Knowledgebase',
                                                                                                                                                                                        'url' => 'knowledgebase.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Downloads',
                                                                                                                                                                                        'url' => 'downloads.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Servers Status',
                                                                                                                                                                                        'url' => 'serverstatus.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                ],
                                                                                                                                                                            ],
                                                                                                                                                                            [
                                                                                                                                                                                'title' => 'Account',
                                                                                                                                                                                'children' => [
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'Client Summary',
                                                                                                                                                                                        'url' => 'clientarea.php',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'My Services',
                                                                                                                                                                                        'url' => 'clientarea.php?action=products',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'My Domains',
                                                                                                                                                                                        'url' => 'clientarea.php?action=domains',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                    [
                                                                                                                                                                                        'title' => 'My Invoices',
                                                                                                                                                                                        'url' => 'clientarea.php?action=invoices',
                                                                                                                                                                                        'urltype' => 'clientarea-off',
                                                                                                                                                                                    ],
                                                                                                                                                                                ],
                                                                                                                                                                            ],
                                                                                                                                                                        ];
                                                                                                                                                                        foreach ($footerMenus as $columnIndex => $column) {
                                                                                                                                                                            $parentId = Manager::table('coodiv__control__panel_items')->insertGetId([
                                                                                                                                                                                'groupid' => $groupid,
                                                                                                                                                                                'topid' => 0,
                                                                                                                                                                                'parentid' => 0,
                                                                                                                                                                                'title' => (string) $column['title'],
                                                                                                                                                                                'url' => '#',
                                                                                                                                                                                'urltype' => 'customurl',
                                                                                                                                                                                'targetwindow' => '_self',
                                                                                                                                                                                'reorder' => $columnIndex + 1,
                                                                                                                                                                                'accesslevel' => 1,
                                                                                                                                                                                'language' => $defaultLanguage,
                                                                                                                                                                                'css_icon' => '',
                                                                                                                                                                                'badge' => 'none',
                                                                                                                                                                                'css_class' => '',
                                                                                                                                                                                'css_id' => '',
                                                                                                                                                                                'datecreate' => $now,
                                                                                                                                                                                'datemodify' => $now,
                                                                                                                                                                            ]);
                                                                                                                                                                            foreach ($column['children'] as $childIndex => $child) {
                                                                                                                                                                                Manager::table('coodiv__control__panel_items')->insert([
                                                                                                                                                                                    'groupid' => $groupid,
                                                                                                                                                                                    'topid' => 0,
                                                                                                                                                                                    'parentid' => $parentId,
                                                                                                                                                                                    'title' => (string) $child['title'],
                                                                                                                                                                                    'url' => (string) $child['url'],
                                                                                                                                                                                    'urltype' => (string) $child['urltype'],
                                                                                                                                                                                    'targetwindow' => '_self',
                                                                                                                                                                                    'reorder' => $childIndex + 1,
                                                                                                                                                                                    'accesslevel' => 1,
                                                                                                                                                                                    'language' => $defaultLanguage,
                                                                                                                                                                                    'css_icon' => '',
                                                                                                                                                                                    'badge' => 'none',
                                                                                                                                                                                    'css_class' => '',
                                                                                                                                                                                    'css_id' => '',
                                                                                                                                                                                    'datecreate' => $now,
                                                                                                                                                                                    'datemodify' => $now,
                                                                                                                                                                                ]);
                                                                                                                                                                            }
                                                                                                                                                                        }
                                                                                                                                                                        $menu->redirect(MODURL . '&action=listitems&groupid=' . $groupid . '&success=1&demofooter=1');
                                                                                                                                                                        exit;
                                                                                                                                                                        goto label_11070;
                                                                                                                                                                        if (0 < $groupid) {
                                                                                                                                                                            Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->delete();
                                                                                                                                                                            Manager::table('coodiv__control__panel__table')->where('id', $groupid)->delete();
                                                                                                                                                                        }
                                                                                                                                                                        exit('Error: ' . $e->getMessage());
                                                                                                                                                                    } else {
                                                                                                                                                                        label_11070:
                                                                                                                                                                        if ($action == 'applynewgroup') {
                                                                                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                            $isPrimary = 2;
                                                                                                                                                                            $isSecondary = 2;
                                                                                                                                                                            if ($_POST['setas'] === 'primary') {
                                                                                                                                                                                $isPrimary = 3;
                                                                                                                                                                                Manager::table('coodiv__control__panel__table')->update(['isprimary' => 0]);
                                                                                                                                                                            }
                                                                                                                                                                            if ($_POST['setas'] === 'secondary') {
                                                                                                                                                                                $isSecondary = 3;
                                                                                                                                                                                Manager::table('coodiv__control__panel__table')->update(['issecondary' => 0]);
                                                                                                                                                                            }
                                                                                                                                                                            $groupid = Manager::table('coodiv__control__panel__table')->insertGetId([
                                                                                                                                                                                'name' => (string) $menu->input($_POST['name']),
                                                                                                                                                                                'template' => (string) $menu->input($_POST['template']),
                                                                                                                                                                                'css_activeclass' => (string) $menu->input($_POST['css_activeclass']),
                                                                                                                                                                                'isprimary' => $isPrimary,
                                                                                                                                                                                'issecondary' => $isSecondary,
                                                                                                                                                                            ]);
                                                                                                                                                                            $menu->redirect(MODURL . '&action=listgroup&success=1');
                                                                                                                                                                            try {
                                                                                                                                                                                exit;
                                                                                                                                                                            } catch (\Exception $e) {
                                                                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                                                                            }
                                                                                                                                                                        } else {
                                                                                                                                                                            if ($action == 'updategroup') {
                                                                                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                $groupid = $menu->input($_GET['id'], 'int');
                                                                                                                                                                                $isPrimary = 2;
                                                                                                                                                                                $isSecondary = 2;
                                                                                                                                                                                if ($menu->input($_POST['setas']) === 'primary') {
                                                                                                                                                                                    $isPrimary = 3;
                                                                                                                                                                                    Manager::table('coodiv__control__panel__table')->update(['isprimary' => 0]);
                                                                                                                                                                                }
                                                                                                                                                                                if ($menu->input($_POST['setas']) === 'secondary') {
                                                                                                                                                                                    $isSecondary = 3;
                                                                                                                                                                                    Manager::table('coodiv__control__panel__table')->update(['issecondary' => 0]);
                                                                                                                                                                                }
                                                                                                                                                                                Manager::table('coodiv__control__panel__table')->where('id', $groupid)->update([
                                                                                                                                                                                    'name' => (string) $menu->input($_POST['name']),
                                                                                                                                                                                    'template' => (string) $menu->input($_POST['template']),
                                                                                                                                                                                    'css_activeclass' => (string) $menu->input($_POST['css_activeclass']),
                                                                                                                                                                                    'isprimary' => $menu->input($isPrimary, 'int'),
                                                                                                                                                                                    'issecondary' => $menu->input($isSecondary, 'int'),
                                                                                                                                                                                ]);
                                                                                                                                                                                $menu->redirect(MODURL . '&action=listgroup&success=1');
                                                                                                                                                                                try {
                                                                                                                                                                                    exit;
                                                                                                                                                                                } catch (\Exception $e) {
                                                                                                                                                                                    exit('Error: ' . $e->getMessage());
                                                                                                                                                                                }
                                                                                                                                                                            } else {
                                                                                                                                                                                if ($action == 'deletegroup') {
                                                                                                                                                                                    shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                    $groupid = $menu->input($_GET['id'], 'int');
                                                                                                                                                                                    Manager::table('coodiv__control__panel__table')->where('id', $groupid)->delete();
                                                                                                                                                                                    Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->delete();
                                                                                                                                                                                    $menu->redirect(MODURL . '&action=listgroup&success=1');
                                                                                                                                                                                    exit;
                                                                                                                                                                                } elseif ($action == 'listitems') {
                                                                                                                                                                                    define('VIEWMENUASADMIN', true);
                                                                                                                                                                                    $groupid = $menu->input($_GET['groupid'], 'int');
                                                                                                                                                                                    $getGroupInfo = Manager::table('coodiv__control__panel__table')->where('id', $groupid)->get();
                                                                                                                                                                                    $groupInfo = $menu->fromMYSQL($getGroupInfo);
                                                                                                                                                                                    $smarty->assign('groupinfo', $groupInfo[0] ?? []);
                                                                                                                                                                                    $homepage = 'homepage.tpl';
                                                                                                                                                                                    $templateFile = 'menulist.tpl';
                                                                                                                                                                                    $menu->addToBreadCrumbs(MODURL . '&action=listgroup', 'Shufy Theme Menu manager');
                                                                                                                                                                                    $menu->addToBreadCrumbs('', $groupInfo[0]['name'] ?? '');
                                                                                                                                                                                    $menuItemsList = [];
                                                                                                                                                                                    $menu->displayFullURL = false;
                                                                                                                                                                                    $menu->checkAccessability = true;
                                                                                                                                                                                    $menuItemsList = $menu->generateMenu($groupid);
                                                                                                                                                                                    $smarty->assign('items', $menuItemsList);
                                                                                                                                                                                    $smarty->assign('countitems', count($menuItemsList));
                                                                                                                                                                                } else {
                                                                                                                                                                                    if ($action == 'additem') {
                                                                                                                                                                                        $groupid = $menu->input($_GET['groupid'], 'int');
                                                                                                                                                                                        $smarty->assign('groupid', $groupid);
                                                                                                                                                                                        $getGroupInfo = Manager::table('coodiv__control__panel__table')->where('id', $groupid)->get();
                                                                                                                                                                                        $groupInfo = $menu->fromMYSQL($getGroupInfo);
                                                                                                                                                                                        $smarty->assign('groupinfo', $groupInfo[0] ?? []);
                                                                                                                                                                                        $menu->addToBreadCrumbs(MODURL . '&action=listgroup', 'Shufy Theme Menu manager');
                                                                                                                                                                                        $menu->addToBreadCrumbs(MODURL . '&action=listitems&groupid=' . ($groupInfo[0]['id'] ?? 0), $groupInfo[0]['name'] ?? '');
                                                                                                                                                                                        $menu->addToBreadCrumbs('', 'Add a New Menu Item');
                                                                                                                                                                                        $templateFile = 'addmenu.tpl';
                                                                                                                                                                                        $getMenuItems = Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->where('parentid', 0)->where('topid', 0)->orderBy('reorder', 'asc')->select('id', 'title')->get();
                                                                                                                                                                                        $level1 = $menu->fromMYSQL($getMenuItems);
                                                                                                                                                                                        $menuItemsList = [];
                                                                                                                                                                                        foreach ($level1 as $index1 => $menulevel1) {
                                                                                                                                                                                            $getMenuItemsLevel2 = Manager::table('coodiv__control__panel_items')->where('parentid', $menulevel1['id'])->where('topid', 0)->orderBy('reorder', 'asc')->select('id', 'title')->get();
                                                                                                                                                                                            $level2 = $menu->fromMYSQL($getMenuItemsLevel2);
                                                                                                                                                                                            $level1[$index1]['sub'] = $level2;
                                                                                                                                                                                            unset($level2);
                                                                                                                                                                                            $menuItemsList = $level2;
                                                                                                                                                                                        }
                                                                                                                                                                                        $smarty->assign('parentlist', $menuItemsList);
                                                                                                                                                                                    } elseif ($action == 'doadditem') {
                                                                                                                                                                                        shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                        $groupid = $menu->input($_POST['groupid'], 'int');
                                                                                                                                                                                        $parentid = $menu->input($_POST['parentid'], 'int');
                                                                                                                                                                                        shufyTheme_validate_menu_parent_depth($parentid, $groupid);
                                                                                                                                                                                        $postedUrltype = $menu->input($_POST['urltype'] ?? '');
                                                                                                                                                                                        $urltype = shufyTheme_normalize_menu_url_type($postedUrltype);
                                                                                                                                                                                        $url = $_POST[$urltype] ?? '';
                                                                                                                                                                                        $getReorder = Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->where('parentid', $parentid)->where('topid', 0)->orderBy('reorder', 'desc')->select('reorder')->take(1)->get();
                                                                                                                                                                                        $reorder = $menu->fromMYSQL($getReorder);
                                                                                                                                                                                        $newReorder = (int) ($reorder[0]['reorder'] ?? 0) + 1;
                                                                                                                                                                                        $itemID = Manager::table('coodiv__control__panel_items')->insertGetId([
                                                                                                                                                                                            'groupid' => $groupid,
                                                                                                                                                                                            'parentid' => $parentid,
                                                                                                                                                                                            'topid' => 0,
                                                                                                                                                                                            'title' => (string) $menu->input($_POST['title']),
                                                                                                                                                                                            'url' => (string) $menu->input($url),
                                                                                                                                                                                            'urltype' => (string) $urltype,
                                                                                                                                                                                            'targetwindow' => (string) $menu->input($_POST['targetwindow']),
                                                                                                                                                                                            'reorder' => (int) $newReorder,
                                                                                                                                                                                            'accesslevel' => $menu->input($_POST['accesslevel'], 'int'),
                                                                                                                                                                                            'badge' => (string) $menu->input($_POST['badge']),
                                                                                                                                                                                            'css_class' => (string) $menu->input($_POST['css_class']),
                                                                                                                                                                                            'css_id' => (string) $menu->input($_POST['css_id']),
                                                                                                                                                                                            'css_icon' => (string) $menu->input($_POST['css_icon']),
                                                                                                                                                                                            'datecreate' => date('Y-m-d H:i:s'),
                                                                                                                                                                                            'datemodify' => date('Y-m-d H:i:s'),
                                                                                                                                                                                            'language' => (string) $menu->input(strtolower($CONFIG['Language'])),
                                                                                                                                                                                        ]);
                                                                                                                                                                                        if (isset($_POST['menuidorder']) && $menu->input($_POST['menuidorder']) !== '') {
                                                                                                                                                                                            Manager::table('coodiv__control__panel_items')->where('id', $itemID)->update(['reorder' => $menu->input($_POST['menuidorder'])]);
                                                                                                                                                                                        }
                                                                                                                                                                                        foreach ($menu->input($_POST['translation_languages'] ?? [], 'array') as $index => $languagename) {
                                                                                                                                                                                            if ($menu->input($_POST['translation_title'][$languagename]) != '') {
                                                                                                                                                                                                Manager::table('coodiv__control__panel_items')->insert([
                                                                                                                                                                                                    'groupid' => (int) $groupid,
                                                                                                                                                                                                    'topid' => (int) $itemID,
                                                                                                                                                                                                    'parentid' => (int) $parentid,
                                                                                                                                                                                                    'title' => (string) $menu->input($_POST['translation_title'][$languagename]),
                                                                                                                                                                                                    'language' => (string) $languagename,
                                                                                                                                                                                                    'datecreate' => '0000-00-00 00:00:00',
                                                                                                                                                                                                    'datemodify' => '0000-00-00 00:00:00',
                                                                                                                                                                                                ]);
                                                                                                                                                                                            }
                                                                                                                                                                                        }
                                                                                                                                                                                        if (isset($_POST['save']) && $_POST['save'] == 'save') {
                                                                                                                                                                                            $menu->redirect(MODURL . '&action=edititem&itemid=' . $itemID . '&success=1');
                                                                                                                                                                                        } else {
                                                                                                                                                                                            $menu->redirect(MODURL . '&action=listitems&groupid=' . $groupid . '&success=1');
                                                                                                                                                                                        }
                                                                                                                                                                                        try {
                                                                                                                                                                                            exit;
                                                                                                                                                                                        } catch (\Exception $e) {
                                                                                                                                                                                            exit('Error: ' . $e->getMessage());
                                                                                                                                                                                        }
                                                                                                                                                                                    } else {
                                                                                                                                                                                        if ($action == 'edititem') {
                                                                                                                                                                                            $itemid = $menu->input($_GET['itemid'], 'int');
                                                                                                                                                                                            $smarty->assign('itemid', $itemid);
                                                                                                                                                                                            $defaultLanguage = strtolower($CONFIG['Language']);
                                                                                                                                                                                            $getItemInfo = Manager::table('coodiv__control__panel_items')->where('id', $itemid)->get();
                                                                                                                                                                                            $itemInfo = $menu->fromMYSQL($getItemInfo);
                                                                                                                                                                                            if (!empty($itemInfo[0])) {
                                                                                                                                                                                                $itemInfo[0]['datecreate'] = date('dS M, Y H:s', strtotime($itemInfo[0]['datecreate']));
                                                                                                                                                                                                $itemInfo[0]['datemodify'] = date('dS M, Y H:s', strtotime($itemInfo[0]['datemodify']));
                                                                                                                                                                                                $itemInfo[0]['url_for_select'] = html_entity_decode((string) ($itemInfo[0]['url'] ?? ''), ENT_QUOTES, 'UTF-8');
                                                                                                                                                                                            }
                                                                                                                                                                                            $itemtranslations = ['title' => [], 'records' => []];
                                                                                                                                                                                            $getItemTranslations = Manager::table('coodiv__control__panel_items')->where('topid', $itemid)->orderBy('id', 'desc')->select('id', 'title', 'language')->get();
                                                                                                                                                                                            foreach ($menu->fromMYSQL($getItemTranslations) as $index => $data) {
                                                                                                                                                                                                if (!array_key_exists($data['language'], $itemtranslations['title'])) {
                                                                                                                                                                                                    $itemtranslations['title'][$data['language']] = $data['title'];
                                                                                                                                                                                                }
                                                                                                                                                                                                $itemtranslations['records'][] = $data['language'] . '-' . $data['id'];
                                                                                                                                                                                            }
                                                                                                                                                                                            if (isset($itemInfo[0]['language']) && $itemInfo[0]['language'] !== '' && !array_key_exists($itemInfo[0]['language'], $itemtranslations['title'])) {
                                                                                                                                                                                                $itemtranslations['title'][$itemInfo[0]['language']] = $itemInfo[0]['title'] ?? '';
                                                                                                                                                                                            }
                                                                                                                                                                                            if (isset($itemInfo[0]['language']) && $itemInfo[0]['language'] != $defaultLanguage && !empty($itemtranslations['title'][$defaultLanguage])) {
                                                                                                                                                                                                $itemInfo[0]['title'] = $itemtranslations['title'][$defaultLanguage];
                                                                                                                                                                                                unset($itemtranslations['title'][$defaultLanguage]);
                                                                                                                                                                                            }
                                                                                                                                                                                            $smarty->assign('itemtranslations', $itemtranslations);
                                                                                                                                                                                            $smarty->assign('totaltranslations', count($itemtranslations['title']));
                                                                                                                                                                                            $smarty->assign('itemtranslationrecords', join(',', $itemtranslations['records']));
                                                                                                                                                                                            $smarty->assign('iteminfo', $itemInfo[0] ?? []);
                                                                                                                                                                                            $getGroupInfo = Manager::table('coodiv__control__panel__table')->where('id', $itemInfo[0]['groupid'] ?? 0)->get();
                                                                                                                                                                                            $groupInfo = $menu->fromMYSQL($getGroupInfo);
                                                                                                                                                                                            $smarty->assign('groupinfo', $groupInfo[0] ?? []);
                                                                                                                                                                                            $getSupportDepartments = Manager::table('tblticketdepartments')->orderBy('id', 'asc')->select('id', 'name')->get();
                                                                                                                                                                                            $smarty->assign('supportdepartments', $menu->fromMYSQL($getSupportDepartments));
                                                                                                                                                                                            $templateFile = 'edit_menu.tpl';
                                                                                                                                                                                            $menu->addToBreadCrumbs(MODURL . '&action=listgroup', 'Shufy Theme Menu manager');
                                                                                                                                                                                            $menu->addToBreadCrumbs(MODURL . '&action=listitems&groupid=' . ($groupInfo[0]['id'] ?? 0), $groupInfo[0]['name'] ?? '');
                                                                                                                                                                                            $menu->addToBreadCrumbs('', 'Edit ' . ($itemInfo[0]['title'] ?? ''));
                                                                                                                                                                                        } elseif ($action == 'doedititem') {
                                                                                                                                                                                            shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                            $postedUrltype = $menu->input($_POST['urltype'] ?? '');
                                                                                                                                                                                            $urltype = shufyTheme_normalize_menu_url_type($postedUrltype);
                                                                                                                                                                                            $url = $_POST[$urltype] ?? '';
                                                                                                                                                                                            Manager::table('coodiv__control__panel_items')->where('id', $menu->input($_POST['itemid'], 'int'))->update([
                                                                                                                                                                                                'title' => (string) $menu->input($_POST['title']),
                                                                                                                                                                                                'url' => (string) $menu->input($url),
                                                                                                                                                                                                'urltype' => (string) $urltype,
                                                                                                                                                                                                'accesslevel' => $menu->input($_POST['accesslevel'], 'int'),
                                                                                                                                                                                                'reorder' => $menu->input($_POST['menuidorder']),
                                                                                                                                                                                                'targetwindow' => (string) $menu->input($_POST['targetwindow']),
                                                                                                                                                                                                'badge' => (string) $menu->input($_POST['badge']),
                                                                                                                                                                                                'css_class' => (string) $menu->input($_POST['css_class']),
                                                                                                                                                                                                'css_id' => (string) $menu->input($_POST['css_id']),
                                                                                                                                                                                                'css_icon' => (string) $menu->input($_POST['css_icon']),
                                                                                                                                                                                                'datemodify' => date('Y-m-d H:i:s'),
                                                                                                                                                                                                'language' => (string) $menu->input(strtolower($CONFIG['Language'])),
                                                                                                                                                                                            ]);
                                                                                                                                                                                            $translationIDs = [];
                                                                                                                                                                                            $translationRecordList = trim((string) $menu->input($_POST['translationrecords']));
                                                                                                                                                                                            if ($translationRecordList !== '') {
                                                                                                                                                                                                $translationRecords = explode(',', $translationRecordList);
                                                                                                                                                                                                foreach ($translationRecords as $record) {
                                                                                                                                                                                                    $splitRecord = explode('-', $record, 2);
                                                                                                                                                                                                    if (count($splitRecord) === 2 && $splitRecord[0] !== '' && $splitRecord[1] !== '') {
                                                                                                                                                                                                        $translationIDs[$splitRecord[0]][] = $splitRecord[1];
                                                                                                                                                                                                    }
                                                                                                                                                                                                }
                                                                                                                                                                                            }
                                                                                                                                                                                            if (isset($_POST['translation_languages']) && is_array($_POST['translation_languages'])) {
                                                                                                                                                                                                foreach ($menu->input($_POST['translation_languages'], 'array') as $index => $languagename) {
                                                                                                                                                                                                    if ($menu->input($_POST['translation_title'][$languagename]) != '') {
                                                                                                                                                                                                        if (array_key_exists($languagename, $translationIDs)) {
                                                                                                                                                                                                            $recordIDs = $translationIDs[$languagename];
                                                                                                                                                                                                            $recordID = array_shift($recordIDs);
                                                                                                                                                                                                            Manager::table('coodiv__control__panel_items')->where('id', $recordID)->update([
                                                                                                                                                                                                                'title' => (string) $menu->input($_POST['translation_title'][$languagename]),
                                                                                                                                                                                                                'datecreate' => '0000-00-00 00:00:00',
                                                                                                                                                                                                                'datemodify' => '0000-00-00 00:00:00',
                                                                                                                                                                                                            ]);
                                                                                                                                                                                                            foreach ($recordIDs as $duplicateRecordID) {
                                                                                                                                                                                                                Manager::table('coodiv__control__panel_items')->where('id', $duplicateRecordID)->delete();
                                                                                                                                                                                                            }
                                                                                                                                                                                                            unset($translationIDs[$languagename]);
                                                                                                                                                                                                        } else {
                                                                                                                                                                                                            Manager::table('coodiv__control__panel_items')->insert([
                                                                                                                                                                                                                'groupid' => $menu->input($_POST['groupid'], 'int'),
                                                                                                                                                                                                                'topid' => $menu->input($_POST['itemid'], 'int'),
                                                                                                                                                                                                                'parentid' => $menu->input($_POST['parentid'], 'int'),
                                                                                                                                                                                                                'title' => (string) $menu->input($_POST['translation_title'][$languagename]),
                                                                                                                                                                                                                'language' => (string) $languagename,
                                                                                                                                                                                                                'datecreate' => '0000-00-00 00:00:00',
                                                                                                                                                                                                                'datemodify' => '0000-00-00 00:00:00',
                                                                                                                                                                                                            ]);
                                                                                                                                                                                                        }
                                                                                                                                                                                                    }
                                                                                                                                                                                                }
                                                                                                                                                                                            }
                                                                                                                                                                                            foreach ($translationIDs as $lang => $recordids) {
                                                                                                                                                                                                foreach ($recordids as $recordid) {
                                                                                                                                                                                                    Manager::table('coodiv__control__panel_items')->where('id', $recordid)->delete();
                                                                                                                                                                                                }
                                                                                                                                                                                            }
                                                                                                                                                                                            if (isset($_POST['save']) && $menu->input($_POST['save']) == 'save') {
                                                                                                                                                                                                $menu->redirect(MODURL . '&action=edititem&itemid=' . $menu->input($_POST['itemid'], 'int') . '&success=1');
                                                                                                                                                                                            } else {
                                                                                                                                                                                                $menu->redirect(MODURL . '&action=listitems&groupid=' . $menu->input($_POST['groupid'], 'int') . '&success=1');
                                                                                                                                                                                            }
                                                                                                                                                                                            try {
                                                                                                                                                                                                exit;
                                                                                                                                                                                            } catch (\Exception $e) {
                                                                                                                                                                                                exit('Error: ' . $e->getMessage());
                                                                                                                                                                                            }
                                                                                                                                                                                        } else {
                                                                                                                                                                                            if ($action == 'reorder') {
                                                                                                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                                $groupid = $menu->input($_POST['groupid'] ?? 0, 'int');
                                                                                                                                                                                                $items = shufyTheme_decode_menu_reorder_payload();
                                                                                                                                                                                                if ($groupid <= 0) {
                                                                                                                                                                                                    throw new Exception('Missing menu group.');
                                                                                                                                                                                                }
                                                                                                                                                                                                if (empty($items) && 0 < Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->where('topid', 0)->count()) {
                                                                                                                                                                                                    throw new Exception('Menu order could not be saved because the submitted menu structure was empty. Please refresh the page and try again.');
                                                                                                                                                                                                }
                                                                                                                                                                                                $submittedIds = [];
                                                                                                                                                                                                shufyTheme_collect_menu_reorder_ids($items, 1, $submittedIds);
                                                                                                                                                                                                $expectedItems = Manager::table('coodiv__control__panel_items')->where('groupid', $groupid)->where('topid', 0)->count();
                                                                                                                                                                                                if (count($submittedIds) !== (int) $expectedItems) {
                                                                                                                                                                                                    throw new Exception('Menu order could not be saved because not all menu items were submitted. Please refresh the page and try again.');
                                                                                                                                                                                                }
                                                                                                                                                                                                $seen = [];
                                                                                                                                                                                                shufyTheme_reorder_menu_items_tree($items, $groupid, 0, 1, $seen);
                                                                                                                                                                                                header('Content-Type: application/json');
                                                                                                                                                                                                try {
                                                                                                                                                                                                    echo json_encode(['success' => true, 'message' => 'Menu order has been saved successfully.']);
                                                                                                                                                                                                } catch (\Exception $e) {
                                                                                                                                                                                                    http_response_code(400);
                                                                                                                                                                                                    header('Content-Type: application/json');
                                                                                                                                                                                                    echo json_encode(['success' => false, 'message' => $e->getMessage()]);
                                                                                                                                                                                                }
                                                                                                                                                                                                exit;
                                                                                                                                                                                            } elseif ($action == 'deleteitem') {
                                                                                                                                                                                                shufy_check_version_or_redirect(SHUFYTHEME_ADDON_VERSION);
                                                                                                                                                                                                $itemid = $menu->input($_GET['id'], 'int');
                                                                                                                                                                                                $groupid = $menu->input($_GET['groupid'], 'int');
                                                                                                                                                                                                Manager::table('coodiv__control__panel_items')->where('id', $itemid)->orWhere('topid', $itemid)->orWhere('parentid', $itemid)->delete();
                                                                                                                                                                                                $menu->redirect(MODURL . '&action=listitems&groupid=' . $groupid . '&success=1');
                                                                                                                                                                                                exit;
                                                                                                                                                                                            }
                                                                                                                                                                                        }
                                                                                                                                                                                    }
                                                                                                                                                                                }
                                                                                                                                                                            }
                                                                                                                                                                        }
                                                                                                                                                                    }
                                                                                                                                                                }
                                                                                                                                                            }
                                                                                                                                                        }
                                                                                                                                                    }
                                                                                                                                                }
                                                                                                                                            }
                                                                                                                                        }
                                                                                                                                    }
                                                                                                                                }
                                                                                                                            }
                                                                                                                        }
                                                                                                                    }
                                                                                                                }
                                                                                                            }
                                                                                                        }
                                                                                                    }
                                                                                                }
                                                                                            }
                                                                                        }
                                                                                    }
                                                                                }
                                                                            }
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    $smarty->assign('breadcrumbs', $menu->getBreadCrumbs());
    $smarty->display('header.tpl');
    if ($licenseactivated) {
        if ($action == '') {
            $smarty->display('homepage.tpl');
        } else {
            $smarty->display($templateFile);
        }
    } else {
        $smarty->display($license__check__pages);
    }
    $smarty->display('footer.tpl');
}

function shufyTheme_sidebar($vars) {
}
// orphan closure from dump: function:7b636c6f737572657d#closure_18

function __closure_c6f737572657d_closure_18($row) {
    return implode(',', $row);
}
// orphan closure from dump: function:7b636c6f737572657d#closure_19

function __closure_c6f737572657d_closure_19($row) {
    return implode(',', $row);
}

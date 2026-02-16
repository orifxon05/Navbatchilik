/*
 * NAVBATCHILIK - Orifxon Marufxonov
 * v1.3.1 - Optimallashtirish va dizayn yangilanishi
 */
package com.navbatchilik.app;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;

public class MainActivity extends Activity {

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        webView = findViewById(R.id.webview);
        Button refreshButton = findViewById(R.id.refreshButton);
        
        // Refresh tugmasi
        refreshButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                webView.reload();
            }
        });
        
        // WebView sozlamalari
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        
        // WebViewClient - linklar shu ilovada ochilsin
        webView.setWebViewClient(new WebViewClient());
        
        // WebChromeClient - JavaScript dialoglar uchun
        webView.setWebChromeClient(new WebChromeClient());
        
        webView.loadUrl("https://ttjmchs.streamlit.app/");
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}

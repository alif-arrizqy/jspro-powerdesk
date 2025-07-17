#!/bin/bash

# Bash script untuk mengunduh semua dependencies offline
# Jalankan script ini dari root directory project

echo "🚀 Mengunduh dependencies untuk JSPro PowerDesk..."

# Buat folder-folder yang diperlukan
mkdir -p static/{css,js,fonts,webfonts}

# Daftar file untuk diunduh
declare -A downloads=(
    # Bootstrap CSS dan JS
    ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"]="static/css/bootstrap.min.css"
    ["https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"]="static/js/bootstrap.bundle.min.js"
    
    # Bootstrap Icons
    ["https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css"]="static/css/bootstrap-icons.css"
    ["https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff2"]="static/fonts/bootstrap-icons.woff2"
    ["https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff"]="static/fonts/bootstrap-icons.woff"
    
    # Font Awesome
    ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"]="static/css/all.min.css"
    ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2"]="static/webfonts/fa-solid-900.woff2"
    ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2"]="static/webfonts/fa-regular-400.woff2"
    ["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2"]="static/webfonts/fa-brands-400.woff2"
    
    # Chart.js
    ["https://cdn.jsdelivr.net/npm/chart.js"]="static/js/chart.min.js"
    
    # SockJS
    ["https://cdn.jsdelivr.net/npm/sockjs-client@1.6.1/dist/sockjs.min.js"]="static/js/sockjs.min.js"
)

# Unduh setiap file
total_files=${#downloads[@]}
current_file=0

for url in "${!downloads[@]}"; do
    ((current_file++))
    output_path="${downloads[$url]}"
    filename=$(basename "$output_path")
    
    echo "[$current_file/$total_files] 📥 Mengunduh: $filename"
    
    if wget -q --show-progress "$url" -O "$output_path"; then
        echo "  ✅ Berhasil: $output_path"
    else
        echo "  ❌ Gagal: $output_path"
    fi
done

# Unduh Google Fonts Inter
echo ""
echo "📝 Mengunduh Google Fonts Inter..."

if wget -q "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" \
   --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
   -O "static/css/inter-font.css"; then
    echo "  ✅ Berhasil: static/css/inter-font.css"
    
    # Extract dan unduh font files
    font_urls=$(grep -oP 'url\(\K[^)]+(?=\))' static/css/inter-font.css | tr -d "'\"")
    font_count=0
    
    while IFS= read -r font_url; do
        if [[ $font_url == https://* ]]; then
            ((font_count++))
            font_name="inter-font-$font_count.woff2"
            if wget -q "$font_url" -O "static/fonts/$font_name"; then
                echo "  ✅ Font berhasil: static/fonts/$font_name"
            else
                echo "  ❌ Font gagal: $font_name"
            fi
        fi
    done <<< "$font_urls"
    
    # Update CSS untuk menggunakan font lokal
    sed -i 's|https://[^)]*\/\(inter-[^)]*\.woff2\?\)|../fonts/\1|g' static/css/inter-font.css
    
else
    echo "  ❌ Gagal mengunduh Google Fonts"
fi

# Perbaiki path di CSS files
echo ""
echo "🔧 Memperbaiki path font di CSS files..."

# Perbaiki Bootstrap Icons CSS
if [ -f "static/css/bootstrap-icons.css" ]; then
    sed -i 's|url("\.\.\/fonts\/bootstrap-icons\.woff2?[^"]*")|url("../fonts/bootstrap-icons.woff2")|g' static/css/bootstrap-icons.css
    sed -i 's|url("\.\.\/fonts\/bootstrap-icons\.woff?[^"]*")|url("../fonts/bootstrap-icons.woff")|g' static/css/bootstrap-icons.css
    echo "  ✅ Bootstrap Icons CSS diperbaiki"
fi

# Perbaiki Font Awesome CSS
if [ -f "static/css/all.min.css" ]; then
    sed -i 's|\.\.\/webfonts\/|../webfonts/|g' static/css/all.min.css
    echo "  ✅ Font Awesome CSS diperbaiki"
fi

echo ""
echo "🎉 Semua dependencies berhasil diunduh!"
echo "📁 File telah disimpan di folder static/"
echo ""
echo "📂 Struktur folder:"
echo "static/"
echo "├── css/"
echo "│   ├── bootstrap.min.css"
echo "│   ├── bootstrap-icons.css"
echo "│   ├── all.min.css"
echo "│   └── inter-font.css"
echo "├── js/"
echo "│   ├── bootstrap.bundle.min.js"
echo "│   ├── chart.min.js"
echo "│   └── sockjs.min.js"
echo "├── fonts/"
echo "│   ├── bootstrap-icons.woff2"
echo "│   ├── bootstrap-icons.woff"
echo "│   └── inter-font-*.woff2"
echo "└── webfonts/"
echo "    ├── fa-solid-900.woff2"
echo "    ├── fa-regular-400.woff2"
echo "    └── fa-brands-400.woff2"
echo ""
echo "🌐 Sekarang aplikasi Anda dapat berjalan tanpa koneksi internet!"

// Gemini API configuration
const API_KEY = "AIzaSyCXiGGBd2KgDVfY_jclNmomk_BWWGUDG0A";
const API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent";

// System prompt
const SYSTEM_PROMPT = `
Bạn là một trợ lý AI thân thiện và thông minh của một website thương mại điện tử.

🎯 Mục tiêu của bạn:
- Trả lời các câu hỏi liên quan đến sản phẩm, đơn hàng, tài khoản, đổi mật khẩu, hủy đơn hàng...
- Hướng dẫn dễ hiểu, chi tiết, thân thiện và tự nhiên như đang trò chuyện.
- Có thể gợi ý sản phẩm phù hợp theo yêu cầu, ngân sách, nhu cầu người dùng.
- Có thể trả lời linh hoạt các câu hỏi ngoài luồng như tâm sự, mẹo cuộc sống, tình cảm, học tập...

---

🛒 Khi người dùng hỏi về **các sản phẩm đang giảm giá** (hoặc từ khóa: giảm giá, khuyến mãi, đang sale...):
- Duyệt danh sách sản phẩm trong context.
- Lọc ra sản phẩm có \`discount > 0\`.
- Tính giá sau khi giảm:
  → \`giá_thực_tế = price - (price * discount / 100)\`
- Trả lời theo định dạng:
  - **[Tên sản phẩm]** – 🏷️ Giảm [XX]%
    ~~[Giá gốc]₫~~ ➡️ **[Giá sau giảm]₫**
    [Xem sản phẩm](link sản phẩm)
- Luôn hiển thị 2-5 sản phẩm có % giảm giá cao nhất.
- Nếu không có sản phẩm nào giảm giá, trả lời chính xác:
  "Hiện tại chưa có sản phẩm nào đang giảm giá trên sàn. Bạn có thể quay lại sau nhé! Trong thời gian này, bạn có muốn mình gợi ý sản phẩm phổ biến nhất không?"

---

📉 Khi người dùng tìm **sản phẩm có giá thấp nhất hoặc cao nhất**:
- Luôn tính theo **giá sau khi giảm** nếu sản phẩm đang khuyến mãi.
- Nếu có nhiều sản phẩm cùng giá, hãy nói:  
  "Đây là một trong những sản phẩm có giá thấp nhất hiện tại…"
- Nếu có giảm giá, ghi rõ:
  - "Giá gốc 150.000₫, sau khi giảm 20% còn **120.000₫**"
- Nếu có đường dẫn sản phẩm, luôn chèn:
  - [Xem sản phẩm](https://example.com/products/123) 🔗

---

💬 Khi người dùng chưa rõ nhu cầu:
- Hỏi lại: “Bạn đang tìm sản phẩm gì? (ví dụ: điện thoại, sách...)”  
- Hoặc: “Bạn muốn mua trong khoảng ngân sách bao nhiêu ạ?”

---

🔐 Một số hướng dẫn nhanh:
- **Đổi mật khẩu:** Vào "Tài khoản của tôi" → "Đổi mật khẩu"
- **Hủy đơn:** Vào "Lịch sử đơn hàng" → Chọn đơn → "Yêu cầu hủy"

---

😊 Ngoài chủ đề thương mại:
- Nếu người dùng hỏi về chuyện tình cảm, cuộc sống, học tập…  
→ Hãy trả lời một cách thân thiện, hài hước nhẹ nhàng, tạo cảm giác gần gũi.

---

📌 Luôn:
- Tránh trả lời rập khuôn.
- Phản hồi tự nhiên như đang chat.
- Giúp người dùng cảm thấy được hỗ trợ thật sự.
- Luôn đính kèm link sản phẩm nếu có thể.
`;

// Chat state
let isChatOpen = false;

// Load chat history when initializing
function loadChatHistory() {
    const chatLog = document.getElementById('chat-log');
    const history = JSON.parse(localStorage.getItem('chat_history')) || [];
    
    // Clear default welcome message
    chatLog.innerHTML = '';
    
    history.forEach(item => {
        const className = item.from === 'bot' ? 'text-green-600' : 'text-blue-600';
        const formattedMessage = formatBotResponse(item.message);
        chatLog.innerHTML += `
            <div class="mb-3">
                <div class="font-bold ${className}">${item.from === 'bot' ? 'Bot' : 'You'}:</div>
                <div class="pl-3 ${item.from === 'bot' ? 'bot-message' : 'user-message'}">${formattedMessage}</div>
            </div>
        `;
    });
    
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Save message to chat history
function saveChatHistory(message, from) {
    const history = JSON.parse(localStorage.getItem('chat_history')) || [];
    history.push({ from, message });
    localStorage.setItem('chat_history', JSON.stringify(history));
}

// Clear chat history
function clearChatHistory() {
    localStorage.removeItem('chat_history');
    const chatLog = document.getElementById('chat-log');
    chatLog.innerHTML = `
        <div class="mb-3">
            <div class="font-bold text-green-600">Bot:</div>
            <div class="pl-3">Hi! How can I help you today?</div>
        </div>
    `;
}

// Validate API key on load
function validateApiKey() {
    if (!API_KEY || API_KEY === "YOUR_API_KEY") {
        console.error("❌ API KEY chưa được thiết lập!");
        alert("Vui lòng cấu hình API KEY hợp lệ!");
        return false;
    }
    return true;
}

// Initialize chat when document is ready
document.addEventListener('DOMContentLoaded', () => {
    if (validateApiKey()) {
        initializeChat();
    }
});

function initializeChat() {
    console.log("🚀 Khởi tạo chatbot...");
    const chatButton = document.getElementById('chatbot-button');
    const chatWindow = document.getElementById('chat-window');
if (chatButton && chatWindow) {
    // Add clear history button
    const chatHeader = chatWindow.querySelector('.p-4');
    chatHeader.innerHTML += `
        <button id="clear-history" onclick="clearChatHistory()" title="Clear chat history">
            <i class="fas fa-trash-alt"></i>
        </button>
    `;
    
    // Load chat history
    loadChatHistory();


        // Handle user input when Enter key is pressed
        const userInput = document.getElementById('user-input');
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMessage();
            }
        });
        console.log("✅ Chatbot đã sẵn sàng!");
    } else {
        console.error("❌ Không tìm thấy các phần tử UI của chatbot!");
    }
}

function toggleChat() {
    if (!validateApiKey()) return;
    
    const chatWindow = document.getElementById('chat-window');
    isChatOpen = !isChatOpen;
    chatWindow.style.display = isChatOpen ? 'block' : 'none';
    
    if (isChatOpen) {
        document.getElementById('user-input').focus();
    }
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    const chatLog = document.getElementById('chat-log');
    
    if (!message) return;

    // Generate unique loading ID
    const loadingId = 'loading-' + Date.now();

    // Add user message with formatting
    const formattedMessage = formatBotResponse(message);
    chatLog.innerHTML += `
        <div class="mb-3">
            <div class="font-bold text-blue-600">You:</div>
            <div class="pl-3 user-message">${formattedMessage}</div>
        </div>
    `;
    saveChatHistory(message, 'user');

    // Clear input and scroll
    userInput.value = '';
    chatLog.scrollTop = chatLog.scrollHeight;

    try {
        // Add loading indicator with typing animation
        chatLog.innerHTML += `
            <div id="${loadingId}" class="mb-3">
                <div class="font-bold text-green-600">Bot:</div>
                <div class="pl-3">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        chatLog.scrollTop = chatLog.scrollHeight;

        // Process message keywords
        const msgLower = message.toLowerCase();
        let contextData = '';

        // Handle password change related questions
        if (msgLower.includes("đổi mật khẩu") || msgLower.includes("password")) {
            contextData = "Hướng dẫn đổi mật khẩu:\n1. Đăng nhập vào tài khoản\n2. Vào mục 'Tài khoản của tôi'\n3. Chọn 'Đổi mật khẩu'\n4. Nhập mật khẩu cũ và mật khẩu mới\n";
        }
        // Handle order cancellation related questions
        else if (msgLower.includes("hủy đơn") || msgLower.includes("cancel")) {
            contextData = "Hướng dẫn hủy đơn hàng:\n1. Đăng nhập vào tài khoản\n2. Vào mục 'Lịch sử đơn hàng'\n3. Tìm đơn hàng cần hủy\n4. Nhấn 'Yêu cầu hủy'\n";
        }
        // Handle product related questions
        else if (msgLower.includes("giảm giá") || msgLower.includes("khuyến mãi") || msgLower.includes("sale")) {
            try {
                const response = await fetch('/api/products');
                if (!response.ok) throw new Error('Failed to fetch products');
                const data = await response.json();
                console.log("📦 All products:", data.products);

                // Validate and filter products with valid discounts
                const discounted = data.products.filter(p => {
                    const discount = Number(p.discount);
                    const isValidDiscount = !isNaN(discount) && discount > 0;
                    console.log(`Product ${p.name}: discount=${p.discount}, isValidDiscount=${isValidDiscount}`);
                    return isValidDiscount;
                });
                
                console.log("🏷️ Products with valid discounts:", discounted);

                if (discounted.length > 0) {
                    // Sort by discount percentage descending
                    discounted.sort((a, b) => {
                        const discountA = Number(a.discount);
                        const discountB = Number(b.discount);
                        return discountB - discountA;
                    });
                    
                    // Take top 5 discounted products
                    const topDiscounted = discounted.slice(0, 5);
                    
                    const formatted = topDiscounted.map(p => {
                        const price = Number(p.price);
                        const discount = Number(p.discount);
                        // Ensure we have valid numbers
                        if (isNaN(price) || isNaN(discount)) {
                            console.error(`Invalid price or discount for product ${p.name}:`, { price, discount });
                            return null;
                        }
                        const finalPrice = price - (price * discount / 100);
                        const productUrl = `${window.location.origin}/products/${p.id}`;
                        return `- **${p.name}** – 🏷️ Giảm ${discount}%\n` +
                               `  ~~${price.toLocaleString()}₫~~ ➡️ **${finalPrice.toLocaleString()}₫**\n` +
                               `  [Xem sản phẩm](${productUrl})`;
                    })
                    .filter(item => item !== null) // Remove any invalid products
                    .join('\n\n');

                    if (formatted) {
                        contextData = `Dưới đây là các sản phẩm đang giảm giá hot nhất:\n\n${formatted}`;
                    } else {
                        contextData = `Hiện tại chưa có sản phẩm nào đang giảm giá trên sàn. Bạn có thể quay lại sau nhé! Trong thời gian này, bạn có muốn mình gợi ý sản phẩm phổ biến nhất không?`;
                    }
                } else {
                    contextData = `Hiện tại chưa có sản phẩm nào đang giảm giá trên sàn. Bạn có thể quay lại sau nhé! Trong thời gian này, bạn có muốn mình gợi ý sản phẩm phổ biến nhất không?`;
                }
            } catch (error) {
                console.error("Error fetching discounted products:", error);
                contextData = "Xin lỗi, hiện tại tôi không thể lấy thông tin sản phẩm giảm giá. Vui lòng thử lại sau.\n";
            }
        } else if (msgLower.includes("sản phẩm") || msgLower.includes("mua") || msgLower.includes("giá")) {
            try {
                // Get price range if mentioned
                let minPrice = 0;
                let maxPrice = Infinity;
                if (msgLower.includes("dưới")) {
                    const priceMatch = message.match(/dưới\s*(\d+)\s*(k|nghìn|triệu|tr)/i);
                    if (priceMatch) {
                        maxPrice = parseInt(priceMatch[1]) * (priceMatch[2].match(/tr|triệu/i) ? 1000000 : 1000);
                    }
                } else if (msgLower.includes("trên")) {
                    const priceMatch = message.match(/trên\s*(\d+)\s*(k|nghìn|triệu|tr)/i);
                    if (priceMatch) {
                        minPrice = parseInt(priceMatch[1]) * (priceMatch[2].match(/tr|triệu/i) ? 1000000 : 1000);
                    }
                }

                // Fetch and filter products
                const response = await fetch('/api/products');
                if (!response.ok) throw new Error('Failed to fetch products');
                const data = await response.json();
                let products = data.products || [];

                // Filter by price if specified
                if (minPrice > 0 || maxPrice < Infinity) {
                    products = products.filter(p => p.price >= minPrice && p.price <= maxPrice);
                }

                // Sort by relevance/price for better suggestions
                if (msgLower.includes("rẻ") || msgLower.includes("giá thấp")) {
                    products.sort((a, b) => a.price - b.price);
                } else if (msgLower.includes("đắt") || msgLower.includes("cao cấp")) {
                    products.sort((a, b) => b.price - a.price);
                }

                // Limit to top 5 most relevant products
                products = products.slice(0, 5);
                // Format products data with absolute URLs and handle discounts
                const formattedProducts = products.map(p => {
                    const productUrl = `${window.location.origin}/products/${p.id}`;
                    const finalPrice = p.discount > 0 ?
                        p.price - (p.price * p.discount / 100) :
                        p.price;
                    const discount = p.discount || 0;
                    return {
                        name: p.name,
                        price: p.price,
                        finalPrice: finalPrice,
                        discount: discount,
                        url: productUrl,
                        description: p.description || ''
                    };
                });

                contextData = `Dựa trên yêu cầu của bạn, đây là một số sản phẩm phù hợp:\n${
                    formattedProducts.map(p => {
                        const priceDisplay = p.discount > 0 ?
                            `<del>${p.price.toLocaleString()}₫</del> ➡️ **${p.finalPrice.toLocaleString()}₫** 🏷️ (-${p.discount}%)` :
                            `${p.price.toLocaleString()}₫`;
                        
                        return `- **${p.name}** - ${priceDisplay}\n` +
                               `  [Xem chi tiết](${p.url}) 🔗\n` +
                               `  ${p.description}\n`;
                    }).join('\n')
                }\n`;
            } catch (error) {
                console.error("Error fetching products:", error);
                contextData = "Xin lỗi, hiện tại tôi không thể lấy thông tin sản phẩm. Vui lòng thử lại sau.\n";
            }
        }

        // Prepare request payload
        const payload = {
            contents: [{
                parts: [{
                    text: SYSTEM_PROMPT + "\n\n" +
                          (contextData ? `Context:\n${contextData}\n\n` : '') +
                          "User: " + message
                }]
            }]
        };

        console.log("📤 Gửi yêu cầu tới Gemini API...", {
            url: API_URL,
            payload: payload
        });

        // Call Gemini API
        const response = await fetch(`${API_URL}?key=${API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("❌ API Error:", response.status, errorText);
            throw new Error(`Lỗi API (${response.status}): ${errorText}`);
        }

        // Validate response content type
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error("Phản hồi không hợp lệ từ Gemini API");
        }

        const data = await response.json();
        console.log("📥 Phản hồi từ Gemini API:", data);

        // Remove loading indicator
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        // Check for error in response
        if (data.error) {
            throw new Error(`Lỗi API: ${data.error.message || 'Không xác định'}`);
        }

        // Check for valid response data
        if (!data.candidates || !data.candidates.length) {
            console.error("❌ Không có dữ liệu phản hồi:", data);
            throw new Error("Không nhận được phản hồi hợp lệ từ Gemini API");
        }

        const reply = data.candidates[0]?.content?.parts?.[0]?.text;
        if (!reply) {
            console.error("❌ Thiếu nội dung phản hồi:", data.candidates[0]);
            throw new Error("Phản hồi không có nội dung");
        }

        // Format and add bot response
        const formattedReply = formatBotResponse(reply);
        chatLog.innerHTML += `
            <div class="mb-3">
                <div class="font-bold text-green-600">Bot:</div>
                <div class="pl-3 whitespace-pre-wrap bot-message">${formattedReply}</div>
            </div>
        `;
        
        // Save bot response to history
        saveChatHistory(reply, 'bot');

        // Scroll to bottom
        chatLog.scrollTop = chatLog.scrollHeight;
        console.log("✅ Xử lý phản hồi thành công!");

    } catch (error) {
        console.error("❌ Lỗi chatbot:", error);

        // Remove loading indicator if still present
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.remove();
        }

        // Add error message
        const errorMessage = error.message || "Có lỗi xảy ra, vui lòng thử lại sau.";
        chatLog.innerHTML += `
            <div class="mb-3">
                <div class="font-bold text-red-600">Lỗi:</div>
                <div class="pl-3">${formatBotResponse(errorMessage)}</div>
            </div>
        `;
        
        // Save error message to history
        saveChatHistory(errorMessage, 'bot');

        // Scroll to bottom
        chatLog.scrollTop = chatLog.scrollHeight;
    }
}

// Format bot response with Markdown-like syntax
function formatBotResponse(text) {
    // Escape HTML first
    text = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // Format product prices
    text = text.replace(/(\d+)000đ/g, (match, price) => {
        const amount = parseInt(price);
        return amount >= 1000 ?
            `${(amount/1000).toLocaleString()}tr đ` :
            `${amount.toLocaleString()}k đ`;
    });

    // Format links
    text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>');

    // Format bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Format strikethrough text
    text = text.replace(/~~(.*?)~~/g, '<del>$1</del>');

    // Format bullet points with better spacing
    text = text.replace(/^- (.*?)$/gm, '<li class="list-disc ml-4 mb-2">$1</li>');

    return text;
}

// Add custom CSS for typing indicator and bot messages
const style = document.createElement('style');
style.textContent = `
    .typing-indicator {
        display: flex;
        gap: 4px;
    }
    .typing-indicator span {
        width: 8px;
        height: 8px;
        background: #10B981;
        border-radius: 50%;
        animation: bounce 1s infinite;
    }
    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-4px); }
    }
    .bot-message, .user-message {
        line-height: 1.5;
        color: #374151;
    }
    .bot-message a {
        color: #2563EB;
        text-decoration: none;
    }
    .bot-message a:hover {
        text-decoration: underline;
    }
    .bot-message strong {
        color: #111827;
        font-weight: 600;
    }
    .user-message {
        color: #1F2937;
        background-color: #F3F4F6;
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    
    /* Chat window size */
    #chat-window {
        width: 400px !important;
        height: auto !important;
    }
    
    #chat-log {
        height: 450px !important;
        font-size: 15px;
    }
    
    /* Clear history button */
    #clear-history {
        position: absolute;
        top: 1rem;
        right: 1rem;
        color: white;
        opacity: 0.7;
        cursor: pointer;
        transition: opacity 0.2s;
    }
    #clear-history:hover {
        opacity: 1;
    }
`;
document.head.appendChild(style);
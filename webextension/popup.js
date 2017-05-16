
chrome.runtime.onMessage.addListener(function (request, sender) {
    if (request.action == "getSource") {
        message.innerText = request.page_url;
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://127.0.0.1:8080/webparser', true);
        xhr.setRequestHeader('Content-Type', 'application/json; charset=UTF-8');
        xhr.send(JSON.stringify(request));
    }
});

function onWindowLoad() {
    var message = document.querySelector('#message');
    chrome.tabs.executeScript(null, {
        file: "getPageSource.js"
    }, function () {
        // If you try and inject into an extensions page or the webstore/NTP you'll get an error
        if (chrome.runtime.lastError) {
            message.innerText = 'There was an error injecting script : \n' + chrome.runtime.lastError.message;
        }
    });
}

window.onload = onWindowLoad;

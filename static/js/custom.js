const yearNow = () => {
    const date = new Date();
    const year = date.getFullYear();
    const yearBar = document.getElementById("dynamic-year");
    yearBar.innerHTML = `&copy ${year}&nbsp;<a target="_blank" href="https://www.sundaya.com/"> Sundaya Indonesia</a>`;
};

const timeNow = () => {
    const date = new Date();
    // day/month/year
    const day = date.getDate();
    const month = date.getMonth() + 1;
    const year = date.getFullYear();
    const tanggal = `${day}/${month}/${year}`;
    // hour:minute:second
    const time = date.toLocaleTimeString("en-US", {
        timeZone: "Asia/Jakarta",
        hour12: false,
    });
    const timeBar = document.getElementById("datetime-bar");
    timeBar.innerHTML = `<b> ${tanggal} ${time}</b>`;
};

yearNow();
setInterval(timeNow, 1000);

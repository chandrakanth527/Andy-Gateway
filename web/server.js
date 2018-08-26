(function() {
    'use strict';

    var es = require('child_process').execSync;
    var binDir = (process.env.WINDIR) ? 'bin\\' : 'bin/';
    // binDir = '';
    var decodeir = binDir + 'decodeir ';
    var encodeir = binDir + 'encodeir ';
    var encodeirz = binDir + 'encodeirz ';

    var code2gc = function(code, compress) {
        if (compress === undefined) compress = true;
        var gc = code.frequency + ',' + (code.repeat[0] + 1) + ',' + (code.repeat[1] + 1);
        var p = [], q = [];
        if (compress) {
            var alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];
            for (var i = 0; i < code.seq.length; i += 2) {
                var j = -1;
                for (var k = 0; k < p.length; k++)
                    if (p[k] === code.seq[i] && q[k] === code.seq[i + 1]) {
                        j = k;
                        break;
                    }
                if (j == -1) {
                    if (p.length < 15) {
                        p.push(code.seq[i]);
                        q.push(code.seq[i + 1]);
                    }
                    gc += ',' + code.seq[i] + ',' + code.seq[i + 1];
                }
                else {
                    gc += alphabet[j];
                }
            }
            gc = gc.replace(/([A-Z]),/g, '$1');
        }
        else {
            gc += ',' + JSON.stringify(code.seq).replace('[', '').replace(']', '');
        }
        return gc;
    }

    var gc2trigger = function(gc) {
        gc = gc.replace(/([A-Z])/g, ',$1,').replace(/,,/g, ',').replace(/,+$/, '');
        // console.log(gc);
        var data = gc.split(',');
        if (data[0] === 'sendir') {
            data.shift();
            data.shift();
            data.shift();
        }
        var f = parseInt(data.shift());
        var r = parseInt(data.shift());
        var o = parseInt(data.shift());
        var trigger = [];
        var p = {}, q = {}, k = 0;
        var alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];
        while (data.length > 0) {
            var v = data.shift();
            if (v.match(/[A-Z]/)) {
                trigger.push(p[v]);
                trigger.push(q[v]);
            }
            else {
                v = parseInt(parseInt(v) * 1000000.0 / f + 0.5);
                trigger.push(v);
                p[alphabet[k]] = v;
                v = parseInt(parseInt(data.shift()) * 1000000.0 / f + 0.5);
                trigger.push(v);
                q[alphabet[k]] = v;
                k++;
            }
        }
        return trigger;
    }

    var rawcode = function(trigger, frequency) {
        if (frequency === undefined) frequency = 37000;
        var seq = [];

        for (var i = 0; i < trigger.length; i++) {
            seq.push(Math.floor(trigger[i] * frequency / 1000000.0 + 0.5));
        }

        return {frequency: frequency, n: seq.length, seq: seq, repeat: [0, 0, 0]};
    }

    var analyse = function(trigger) {
        var args, spec, code;
        var response = { confidence: 0 };
        if (trigger[0] !== '0000') { // If not Pronto HEX
            for (var i = 0; i < trigger.length; i++) trigger[i] = parseInt(trigger[i]);
            if (trigger.length % 2 == 1) trigger.push(100000);
        }
        spec = JSON.parse(es(decodeir + trigger.join(' ')).toString().trim());
        if (spec.error === undefined) {
            response.confidence += 32;
            response.spec = spec;
            args = spec.protocol + ' ' + spec.device + ' ' + (spec.subdevice || -1) + ' ' + spec.obc;
            code = JSON.parse(es(encodeirz + args).toString().trim());
            if (code.error === undefined) {
                response.confidence += 64;
                code.repeat[0] = 1;
                response.code = code2gc(code);
                if (spec.misc && spec.misc.match(/T=/)) {
                    args += ' 1';
                    code = JSON.parse(es(encodeirz + args).toString().trim());
                    code.repeat[0] = 1;
                    response.tcode = code2gc(code);
                }
            }
            else {
                // console.log('encode error');
                response.trigger = trigger;
                code = rawcode(trigger);
                response.code = code2gc(code);
            }
        }
        else {
            // console.log('decode error');
            response.trigger = trigger;
            code = rawcode(trigger);
            response.code = code2gc(code);
        }
        return response;
    }

    // Server
    var restify = require('restify'),
        fs = require('fs');

    var server = restify.createServer();
    server.pre(restify.pre.sanitizePath());
    server.use(restify.acceptParser(server.acceptable));
    server.use(restify.queryParser());
    server.use(restify.bodyParser());

  server.get('/readConfig/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });

        if (!fs.existsSync("/home/pi/andy/cfg/"+req.params.filename)) {
           res.send(404);
        }
        fs.readFile("/home/pi/andy/cfg/"+req.params.filename, 'utf8', function (err,data) {
        if (err) {
           res.end(error);
        }
           res.end(data);
        });
        return next();
    });

  server.get('/syncRead/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });

        if (!fs.existsSync("/home/pi/andy/syncData/"+req.params.filename)) {
           res.send(404);
        }
        fs.readFile("/home/pi/andy/syncData/"+req.params.filename, 'utf8', function (err,data) {
        if (err) {
           res.end(error);
        }
           res.end(data);
        });
        return next();
    });

  server.get('/writeSerial/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
        require("child_process").exec('python send_serial.py '+req.params.serialData).unref();
        res.end("OK");
        return next();
    });

 server.post('/cfgWrite/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
        try {
            fs.accessSync('/home/pi/andy/cfg/', fs.W_OK);
        }
        catch (error) {
            fs.mkdirSync('/home/pi/andy/cfg');
        }

        fs.writeFile('/home/pi/andy/cfg/' + req.body.filename, req.body.data, function(error) {
            if (error)
                res.end(JSON.stringify({status: 'error', error: error}));
            else
                res.end(JSON.stringify({status: 'ok'}));
            return next();
        });
    });


  server.post('/syncWrite/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
        try {
            fs.accessSync('/home/pi/andy/syncData/', fs.W_OK);
        }
        catch (error) {
            fs.mkdirSync('/home/pi/andy/syncData');
        }

        fs.writeFile('/home/pi/andy/syncData/' + req.body.filename, req.body.data, function(error) {
            if (error)
                res.end(JSON.stringify({status: 'error', error: error}));
            else
                res.end(JSON.stringify({status: 'ok'}));
            return next();
        });
    });

  server.post('/masterWrite/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
        try {
            fs.accessSync('/home/pi/andy/cfg/', fs.W_OK);
        }
        catch (error) {
            fs.mkdirSync('/home/pi/andy/cfg');
        }

        fs.writeFile('/home/pi/andy/cfg/' + req.body.filename, req.body.data, function(error) {
            if (error)
                res.end(JSON.stringify({status: 'error', error: error}));
            else
                require("child_process").exec('python /home/pi/andy/master/createStatus.py').unref();
                res.end(JSON.stringify({status: 'ok'}));

            return next();
        });
    });


  server.get('/readRemote/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
       var fs = require('fs');
       var files= [];
       var remotes='{"REMOTECONTROLS":[]}';
       var parse_remotes=JSON.parse(remotes);
       var obj;
       fs.readdir('/home/pi/andy/remotes/', function (err, list) {
       if(err) throw err;
       for(var i=0; i<list.length; i++)
       {
           var name = '/home/pi/andy/remotes/' + list[i];
           if(!err && !fs.statSync(name).isDirectory()) {
            files.push(list[i]); 
            var data = fs.readFileSync(name, 'utf8');
            obj = JSON.parse(data);
            parse_remotes['REMOTECONTROLS'].push(obj);
          }

       }

       var jsonString = JSON.stringify(parse_remotes);
       res.end(jsonString);
       });
      return next();
    });


 server.get('/readRemote1/', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
       var fs = require('fs');
       var files= [];
       var remotes='{"REMOTECONTROLS":[]}';
       var parse_remotes=JSON.parse(remotes);
       var obj;
       fs.readdir('/home/pi/andy/remotes/', function (err, list) {
       if(err) throw err;
       for(var i=0; i<list.length; i++)
       {
           var name = '/home/pi/andy/remotes/' + list[i];
           if(!err && !fs.statSync(name).isDirectory()) {
            files.push(list[i]);
            fs.readFile(name, 'utf8', function (err,data) {
               if (err) {
                 res.end(error);
               }
               console.log(i);
               console.log(list.length);
               obj = JSON.parse(data);
               parse_remotes['REMOTECONTROLS'].push(obj);

             });
            }

       }

       var jsonString = JSON.stringify(parse_remotes);
       res.end(jsonString);
       });
        console.log(JSON.stringify(parse_remotes));
        return next();
    });


    server.get('/irp/analyse/:data', function(req, res, next) {
        try {
            var trigger;
            try {
                var v1form = JSON.parse(req.params.data);
                var sendir = 'sendir,1:1,0,' + v1form.frequency + ',1,1';
                for (var i = 0; i < v1form.n; i++)
                    sendir += ',' + v1form.seq[i];
                trigger = gc2trigger(sendir);
            }
            catch (error) {
                trigger = req.params.data.replace(/,/g, ' ').replace(/ +/g, ' ').trim().split(' ');
            }
            if (trigger[0] === 'sendir') {
                trigger = gc2trigger(req.params.data);
            }
            else if (isNaN(parseInt(trigger[0])) && (trigger.length == 3 || trigger.length == 4)) {
                if (trigger.length == 3)
                    trigger.splice(2, 0, -1);
                trigger = es(encodeir + trigger.join(' ')).toString().split(' ');
            }
            var response = JSON.stringify(analyse(trigger));
            res.writeHead(200, {
                'Content-Type': 'application/json; charset=utf-8'
            });
            res.end(response);
        } catch (err) {
            console.log(err);
            res.end();
        }
        return next();
    });

    server.post('/remotes/write', function(req, res, next) {
        res.writeHead(200, {
            'Content-Type': 'application/json; charset=utf-8'
        });
        try {
            fs.accessSync('/home/pi/andy/remotes/', fs.W_OK);
        }
        catch (error) {
            fs.mkdirSync('/home/pi/andy/remotes');
        }
        fs.writeFile('/home/pi/andy/remotes/' + req.body.filename, JSON.stringify(req.body.remote), function(error) {
            if (error)
                res.end(JSON.stringify({status: 'error', error: error}));
            else
                res.end(JSON.stringify({status: 'ok'}));
            return next();
        });
    });

    server.listen(process.env.PORT || 80, function() {
        console.log('Andy listening at %s', server.url);
    });

}());

